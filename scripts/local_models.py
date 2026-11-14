"""Resolve and verify local Ollama target models from ``configs/models.yaml``.

Keeps local Ollama inference decoupled from ``external/pander-score`` and private API
credentials while providing a uniform ``resolve_target_model`` entry point for both local
and API targets.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml
from inspect_ai.model import ChatMessageUser, GenerateConfig, Model, get_model

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs" / "models.yaml"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"

_ALIAS_SHORTHANDS = {
    "qwen": "qwen-3.8-27b",
    "qwen-sprint": "qwen-3.8-27b",
    "mistral": "mistral-small-3.1-24b",
    "mistral-sprint": "mistral-small-3.1-24b",
}


def load_models(config_path: Path = CONFIG) -> dict[str, Any]:
    """Load the model registry YAML without requiring external dependencies."""
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def normalize_local_alias(alias: str, config_path: Path = CONFIG) -> str:
    """Resolve a canonical or shorthand local alias to its key in ``local_models``."""
    cfg = load_models(config_path)
    local_models = cfg.get("local_models") or {}
    if alias in local_models:
        return alias
    mapped = _ALIAS_SHORTHANDS.get(alias)
    if mapped and mapped in local_models:
        return mapped
    for canonical, spec in local_models.items():
        if alias in (spec.get("ollama_model"), spec.get("base_model")):
            return canonical
    raise KeyError(
        f"{alias!r} is not a configured local model in {config_path}. "
        f"Available: {', '.join(local_models)}"
    )


def is_local_target(alias: str, config_path: Path = CONFIG) -> bool:
    """Return True if *alias* maps to a configured local Ollama model."""
    try:
        normalize_local_alias(alias, config_path=config_path)
    except KeyError:
        return False
    return True


def list_local_targets(config_path: Path = CONFIG) -> list[str]:
    """Return the configured local target aliases in declaration order."""
    return list(load_models(config_path).get("local_targets") or [])


def get_local_spec(alias: str, config_path: Path = CONFIG) -> dict[str, Any]:
    """Return the configuration dictionary for a local target alias."""
    canonical = normalize_local_alias(alias, config_path=config_path)
    return dict(load_models(config_path)["local_models"][canonical])


def _merge_extra_body(
    base: dict[str, Any] | None, override: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not base and not override:
        return None
    merged: dict[str, Any] = copy.deepcopy(base or {})
    for key, val in (override or {}).items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_extra_body(merged[key], val)
        else:
            merged[key] = copy.deepcopy(val)
    return merged


def local_generate_config(
    alias: str, config_path: Path = CONFIG, **overrides: Any
) -> GenerateConfig:
    """Build a ``GenerateConfig`` for a local model, preserving critical ``extra_body``."""
    spec = get_local_spec(alias, config_path=config_path)
    base_extra = spec.get("extra_body")
    override_extra = overrides.pop("extra_body", None)
    merged_extra = _merge_extra_body(base_extra, override_extra)

    params: dict[str, Any] = {
        "temperature": spec.get("temperature", 0.0),
        "max_tokens": spec.get("max_tokens", 2048),
        "max_connections": spec.get("max_connections", 4),
    }
    if merged_extra is not None:
        params["extra_body"] = merged_extra
    for key, val in overrides.items():
        if val is not None:
            params[key] = val
    return GenerateConfig(**params)


def merge_generate_config(base: GenerateConfig, override: GenerateConfig | None) -> GenerateConfig:
    """Merge an optional override ``GenerateConfig`` onto *base*, keeping nested ``extra_body``."""
    if override is None:
        return base
    merged = base.merge(override)
    merged_extra = _merge_extra_body(base.extra_body, override.extra_body)
    if merged_extra is not None:
        merged = merged.merge(GenerateConfig(extra_body=merged_extra))
    return merged


def resolve_ollama_root_url(base_url: str | None = None) -> str:
    """Return the root HTTP URL for the Ollama daemon (without trailing ``/v1``)."""
    raw = (
        base_url
        or os.environ.get("OLLAMA_BASE_URL")
        or os.environ.get("OLLAMA_HOST")
        or DEFAULT_OLLAMA_URL
    ).strip()
    if "://" not in raw:
        raw = f"http://{raw}"
    parsed = urllib.parse.urlparse(raw)
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        path = path[:-3]
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/"), "", "", ""))


def ollama_tags(base_url: str | None = None, timeout_s: float = 5.0) -> set[str]:
    """Query Ollama ``/api/tags`` and return installed model tag names."""
    root_url = resolve_ollama_root_url(base_url)
    url = f"{root_url}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            f"Could not reach Ollama at {url}. Ensure `ollama serve` is running."
        ) from exc
    return {m["name"] for m in payload.get("models", []) if "name" in m}


def _tag_installed(installed: set[str], target: str) -> bool:
    if target in installed:
        return True
    if ":" not in target and f"{target}:latest" in installed:
        return True
    return False


def ensure_local_model_available(
    alias: str,
    *,
    use_base: bool = False,
    base_url: str | None = None,
    config_path: Path = CONFIG,
) -> str:
    """Verify the target Ollama model tag exists locally and return the Ollama model name."""
    spec = get_local_spec(alias, config_path=config_path)
    model_name = spec["base_model"] if use_base else spec["ollama_model"]
    installed = ollama_tags(base_url=base_url)
    if _tag_installed(installed, model_name):
        return model_name

    base_model = spec["base_model"]
    modelfile = spec.get("modelfile", "")
    if not use_base and _tag_installed(installed, base_model):
        raise RuntimeError(
            f"Ollama model {model_name!r} is missing, though base model {base_model!r} is present. "
            f"Run: ollama create {model_name} -f {modelfile}"
        )
    raise RuntimeError(
        f"Ollama model {model_name!r} is not installed. "
        f"Pull {base_model!r} (`ollama pull {base_model}`) and run "
        f"`ollama create {model_name} -f {modelfile}`."
    )


def resolve_local_model(
    alias: str,
    config: GenerateConfig | None = None,
    *,
    use_base: bool = False,
    check_ollama: bool = True,
    base_url: str | None = None,
    config_path: Path = CONFIG,
) -> Model:
    """Resolve a local target alias to an Inspect ``ollama/...`` ``Model``."""
    spec = get_local_spec(alias, config_path=config_path)
    model_name = (
        ensure_local_model_available(
            alias, use_base=use_base, base_url=base_url, config_path=config_path
        )
        if check_ollama
        else (spec["base_model"] if use_base else spec["ollama_model"])
    )
    cfg = merge_generate_config(local_generate_config(alias, config_path=config_path), config)
    kwargs: dict[str, Any] = {"config": cfg}
    explicit_v1 = base_url or os.environ.get("OLLAMA_BASE_URL")
    if explicit_v1:
        kwargs["base_url"] = f"{resolve_ollama_root_url(explicit_v1)}/v1"
    return get_model(f"ollama/{model_name}", **kwargs)


def _import_api_models():
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import api_models  # type: ignore

    return api_models


def resolve_target_model(
    alias: str,
    config: GenerateConfig | None = None,
    *,
    use_base: bool = False,
    check_ollama: bool = True,
    config_path: Path = CONFIG,
) -> tuple[Model, dict[str, Any]]:
    """Resolve either a local Ollama alias or a configured API alias to an Inspect ``Model``.

    Returns ``(model, info)`` where ``info`` includes ``kind`` (``'local'`` or ``'api'``),
    ``canonical_alias``, and recommended ``max_connections``.
    """
    if is_local_target(alias, config_path=config_path):
        canonical = normalize_local_alias(alias, config_path=config_path)
        spec = get_local_spec(canonical, config_path=config_path)
        model = resolve_local_model(
            canonical,
            config=config,
            use_base=use_base,
            check_ollama=check_ollama,
            config_path=config_path,
        )
        return model, {
            "kind": "local",
            "canonical_alias": canonical,
            "ollama_model": spec["base_model"] if use_base else spec["ollama_model"],
            "max_connections": spec.get("max_connections", 4),
            "num_ctx": spec.get("num_ctx"),
        }

    cfg = load_models(config_path)
    if alias in (cfg.get("api_targets") or []):
        api_models = _import_api_models()
        model = api_models.resolve_model(alias, config=config)
        return model, {
            "kind": "api",
            "canonical_alias": alias,
            "max_connections": cfg.get("max_connections", 8),
        }

    raise KeyError(
        f"Unknown model alias {alias!r}. Expected one of local_targets "
        f"{cfg.get('local_targets')} or api_targets {cfg.get('api_targets')}."
    )


def setup_modelfiles(
    aliases: list[str] | None = None, config_path: Path = CONFIG
) -> dict[str, str]:
    """Create local Ollama tags from the repo ``models/Modelfile.*`` definitions."""
    targets = [normalize_local_alias(a, config_path=config_path) for a in aliases] if aliases else list_local_targets(config_path)
    installed = ollama_tags()
    created: dict[str, str] = {}
    for alias in targets:
        spec = get_local_spec(alias, config_path=config_path)
        base_model = spec["base_model"]
        if not _tag_installed(installed, base_model):
            raise RuntimeError(
                f"Base model {base_model!r} for {alias} is not installed. Run: ollama pull {base_model}"
            )
        modelfile_path = ROOT / spec["modelfile"]
        if not modelfile_path.exists():
            raise FileNotFoundError(f"Missing Modelfile: {modelfile_path}")
        ollama_name = spec["ollama_model"]
        subprocess.run(
            ["ollama", "create", ollama_name, "-f", str(modelfile_path)],
            check=True,
        )
        created[alias] = ollama_name
    return created


def check_environment(config_path: Path = CONFIG) -> dict[str, Any]:
    """Inspect Ollama availability and verify each configured local target."""
    installed = ollama_tags()
    statuses: dict[str, dict[str, Any]] = {}
    for alias in list_local_targets(config_path):
        spec = get_local_spec(alias, config_path=config_path)
        statuses[alias] = {
            "ollama_model": spec["ollama_model"],
            "ollama_model_ready": _tag_installed(installed, spec["ollama_model"]),
            "base_model": spec["base_model"],
            "base_model_ready": _tag_installed(installed, spec["base_model"]),
            "num_ctx": spec.get("num_ctx"),
            "max_connections": spec.get("max_connections"),
            "extra_body": spec.get("extra_body"),
        }
    return {"ollama_url": resolve_ollama_root_url(), "targets": statuses}


async def _run_smoke(aliases: list[str], batch_size: int) -> None:
    prompt = "In two sentences, weigh one argument for and one argument against carbon taxes."
    for alias in aliases:
        model, info = resolve_target_model(alias)
        async with model:
            outputs = await asyncio.gather(
                *[
                    model.generate([ChatMessageUser(content=prompt)], config=GenerateConfig(max_tokens=96))
                    for _ in range(batch_size)
                ]
            )
        print(
            json.dumps(
                {
                    "alias": info["canonical_alias"],
                    "ollama_model": info.get("ollama_model"),
                    "batch_size": batch_size,
                    "all_nonempty": all(bool(o.completion.strip()) for o in outputs),
                    "tokens": [o.usage.output_tokens if o.usage else None for o in outputs],
                    "sample_prefix": outputs[0].completion.strip()[:90],
                }
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect and manage local Ollama target models.")
    parser.add_argument("--check", action="store_true", help="Verify Ollama daemon and model tags.")
    parser.add_argument(
        "--setup-modelfiles",
        action="store_true",
        help="Run `ollama create` from models/Modelfile.* for configured local targets.",
    )
    parser.add_argument("--smoke", action="store_true", help="Run a minimal batched local smoke test.")
    parser.add_argument("--batch-size", type=int, default=2, help="Concurrent calls for --smoke.")
    parser.add_argument("--model", nargs="*", help="Subset of local model aliases to act on.")
    args = parser.parse_args(argv)

    if args.setup_modelfiles:
        created = setup_modelfiles(args.model)
        print(json.dumps({"created": created}, indent=2))
    if args.check or not (args.setup_modelfiles or args.smoke):
        print(json.dumps(check_environment(), indent=2))
    if args.smoke:
        targets = args.model or list_local_targets()
        asyncio.run(_run_smoke(targets, max(1, args.batch_size)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
