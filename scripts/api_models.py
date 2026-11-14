"""Resolve API target aliases (configs/models.yaml) to Inspect models.

Inspect only ever sees the alias and a placeholder URL. A custom httpx transport sends each request
to the real endpoint (LLM_BASE_URL) with the real model name (LLM_MODEL_MAP), credentials and extra
headers, and returns a response with the alias as model name, identifying response headers dropped
and error bodies replaced by a generic message. So nothing about the endpoint reaches eval logs,
tracebacks or the console.

.env:
  LLM_BASE_URL       real OpenAI-compatible base URL
  LLM_API_KEY        bearer key
  LLM_EXTRA_HEADERS  optional JSON object of request headers
  LLM_MODEL_MAP      JSON object {alias: real model name}
  LLM_DEBUG_ERRORS   optional, "1" prints raw endpoint error bodies to this terminal's stderr
                     (bypasses Inspect, but don't use it when the output is captured or shared)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv
from inspect_ai.model import GenerateConfig, Model, get_model
from openai import DefaultAsyncHttpxClient
from pander_score.core.config import PUBLISHED_MODEL_CONFIGS, resolve_model_config

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs" / "models.yaml"
PLACEHOLDER = "http://api-target.invalid/v1"
_KEEP_RESPONSE_HEADERS = {"content-type", "retry-after"}


def load_models() -> dict:
    return yaml.safe_load(CONFIG.read_text())


def published_id(alias: str) -> str:
    """The one Pander published model id whose last path segment is the alias."""
    hits = [k for k in PUBLISHED_MODEL_CONFIGS if k.rsplit("/", 1)[-1] == alias]
    if len(hits) != 1:
        raise KeyError(f"{alias}: expected one published Pander config, found {len(hits)}")
    return hits[0]


def generate_config(alias: str, **overrides) -> GenerateConfig:
    """Pander's published condition for this model, plus explicit overrides."""
    r = resolve_model_config(published_id(alias), **overrides)
    return GenerateConfig(
        reasoning_effort=r.reasoning_effort,
        temperature=r.temperature,
        max_tokens=r.max_tokens,
        max_connections=load_models()["max_connections"],
    )


class _EndpointTransport(httpx.AsyncBaseTransport):
    def __init__(self, base_url: str, api_key: str, headers: dict, model_map: dict) -> None:
        self._base = base_url.rstrip("/")
        self._auth = {"Authorization": f"Bearer {api_key}", **headers}
        self._to_real = model_map
        self._to_alias = {v: k for k, v in model_map.items()}
        self._inner = httpx.AsyncHTTPTransport(retries=0)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/v1")
        body = await request.aread()
        alias = None
        if body and request.headers.get("content-type", "").startswith("application/json"):
            data = json.loads(body)
            alias = data.get("model")
            if alias not in self._to_real:
                return self._error(request, 400, f"unknown model alias {alias!r}")
            data["model"] = self._to_real[alias]
            body = json.dumps(data).encode()
        drop = {"host", "authorization", "content-length"}
        headers = {k: v for k, v in request.headers.items() if k.lower() not in drop} | self._auth
        upstream = httpx.Request(request.method, self._base + path, headers=headers, content=body,
                                 extensions=request.extensions)
        try:
            resp = await self._inner.handle_async_request(upstream)
            content = await resp.aread()
        except httpx.HTTPError:
            raise httpx.ConnectError("API target endpoint unreachable", request=request) from None
        finally:
            if "resp" in locals():
                await resp.aclose()
        if resp.status_code >= 400:
            if os.environ.get("LLM_DEBUG_ERRORS") == "1":  # local terminal only, never into Inspect
                sys.__stderr__.write(f"[api_models] HTTP {resp.status_code}: {content[:2000]!r}\n")
            return self._error(request, resp.status_code, f"API target endpoint returned HTTP {resp.status_code}",
                               {k: v for k, v in resp.headers.items() if k.lower() == "retry-after"})
        try:
            data = json.loads(content)
        except ValueError:
            return self._error(request, 502, "API target endpoint returned a non-JSON response")
        if isinstance(data, dict) and "model" in data:
            data["model"] = self._to_alias.get(data["model"], alias or "unknown")
        if isinstance(data, dict) and isinstance(data.get("data"), list):  # /models listing
            data["data"] = [{"id": a, "object": "model"} for a in self._to_real]
        if isinstance(data, dict):
            data.pop("system_fingerprint", None)
        keep = {k: v for k, v in resp.headers.items() if k.lower() in _KEEP_RESPONSE_HEADERS}
        keep["content-type"] = "application/json"
        return httpx.Response(resp.status_code, headers=keep, content=json.dumps(data).encode(), request=request)

    @staticmethod
    def _error(request, status, message, headers=None) -> httpx.Response:
        body = {"error": {"message": message, "type": "api_target_error", "code": status}}
        return httpx.Response(status, json=body, headers=headers or {}, request=request)

    async def aclose(self) -> None:
        await self._inner.aclose()


def resolve_model(alias: str, config: GenerateConfig | None = None) -> Model:
    if alias not in load_models()["api_targets"]:
        raise KeyError(f"{alias} is not in api_targets of {CONFIG}")
    load_dotenv(ROOT / ".env")
    missing = [v for v in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL_MAP") if not os.environ.get(v)]
    if missing:
        raise RuntimeError(f"set {', '.join(missing)} in .env")
    model_map = json.loads(os.environ["LLM_MODEL_MAP"])
    if alias not in model_map:
        raise RuntimeError(f"LLM_MODEL_MAP in .env has no entry for {alias}")
    transport = _EndpointTransport(os.environ["LLM_BASE_URL"], os.environ["LLM_API_KEY"],
                                   json.loads(os.environ.get("LLM_EXTRA_HEADERS") or "{}"), model_map)
    return get_model(
        f"openai-api/target/{alias}",
        base_url=PLACEHOLDER,
        api_key="unused",  # the transport adds the real key; Inspect never logs api_key anyway
        http_client=DefaultAsyncHttpxClient(transport=transport),
        config=config or generate_config(alias),
    )
