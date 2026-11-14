"""Full run for the API targets: the 42-proposition set and the 80 known items, both policies.

    uv run --project external/pander-score python -I scripts/run_api_full.py \
        [--models grok-4.6] [--policy both] [--max-connections 16] [--limit N] [--log-dir logs/full]

For each model and policy, two evals of `hedge_hack_eval` (scripts/hedge_hack_pipeline.py):
- "subset": data/full_run/full_run_prompts.jsonl (504 prompts) with the substitute credence judges;
- "known": the 80 known items without judges (they are scored by FINAL: accuracy, and Pander's credence
  judge does not apply to them).
Targets come from the endpoint (api_models.resolve_model, Pander's published settings), judges via
gateway_judges (JUDGE_MODEL_MAP). Logs go to --log-dir with metadata stage "full", target_model, policy, part.

Resilience: target calls use Inspect's cache (judges always do), and errored samples are retried up to 3
times. If a run stops part-way, rerun the same command: finished calls come from the cache at no cost.
Pass --no-cache to force fresh target calls (e.g. a deliberate rerun for noise).

Spend: after every eval, the target and judge dollars at the prices below are printed and appended to
outputs/full/spend.jsonl, with a running total. Target prices are from docs/api_models.md (to confirm);
judge prices are the endpoint's (2026-11-14). Input tokens are priced in full (cache reads not discounted),
so the figures lean high. --limit N runs only the first N prompts of each part (smoke test).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from inspect_ai import eval as inspect_eval

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from api_models import ROOT, generate_config, load_models, resolve_model  # noqa: E402
from hedge_hack_pipeline import hedge_hack_eval  # noqa: E402

FULL_PROMPTS = ROOT / "data" / "full_run" / "full_run_prompts.jsonl"
SPEND_LOG = ROOT / "outputs" / "full" / "spend.jsonl"
# $ per M tokens (input, output)
TARGET_PRICES = {"kimi-k3": (3.0, 15.0), "grok-4.6": (2.0, 6.0)}
JUDGE_PRICES = {"judge-openai": (2.0, 12.0), "judge-google": (1.5, 9.0)}


def usd(usage, prices: tuple[float, float]) -> float:
    return (usage.input_tokens * prices[0] + usage.output_tokens * prices[1]) / 1e6


def spend_of(log, alias: str) -> dict:
    out = {"target_usd": 0.0, "judge_usd": 0.0, "tokens": {}}
    for name, u in (log.stats.model_usage or {}).items():
        short = name.rsplit("/", 1)[-1]
        out["tokens"][short] = [u.input_tokens, u.output_tokens]
        if short == alias:
            out["target_usd"] += usd(u, TARGET_PRICES[alias])
        elif short in JUDGE_PRICES:
            out["judge_usd"] += usd(u, JUDGE_PRICES[short])
    return out


def previous_total() -> float:
    if not SPEND_LOG.exists():
        return 0.0
    rows = [json.loads(l) for l in SPEND_LOG.read_text().splitlines() if l.strip()]
    return sum(r["target_usd"] + r["judge_usd"] for r in rows if not r.get("smoke"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=load_models()["api_targets"])
    ap.add_argument("--policy", choices=["neutral", "hedge_hack", "both"], default="both")
    ap.add_argument("--parts", nargs="+", choices=["subset", "known"], default=["subset", "known"])
    ap.add_argument("--max-connections", type=int, default=16)
    ap.add_argument("--limit", type=int, default=None, help="first N prompts of each part (smoke test)")
    ap.add_argument("--log-dir", type=Path, default=ROOT / "logs" / "full")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()
    smoke = a.limit is not None
    policies = ["neutral", "hedge_hack"] if a.policy == "both" else [a.policy]
    SPEND_LOG.parent.mkdir(parents=True, exist_ok=True)
    running = previous_total()
    print(f"full-run spend logged so far (excluding smoke tests): ${running:.2f}")

    for alias in a.models:
        config = generate_config(alias).model_copy(update={"cache": not a.no_cache})
        model = resolve_model(alias, config)
        for policy in policies:
            for part in a.parts:
                task = hedge_hack_eval(policy=policy, dataset=part, subset_path=str(FULL_PROMPTS),
                                       with_judges=(part == "subset"))
                t0 = time.perf_counter()
                [log] = inspect_eval(task, model=model, log_dir=str(a.log_dir), display="plain",
                                     max_connections=a.max_connections, limit=a.limit,
                                     retry_on_error=3, fail_on_error=0.05,
                                     metadata={"target_model": alias, "policy": policy, "part": part,
                                               "stage": "smoke" if smoke else "full"})
                s = spend_of(log, alias)
                errors = sum(1 for x in (log.samples or []) if x.error is not None)
                cost = s["target_usd"] + s["judge_usd"]
                if not smoke:
                    running += cost
                row = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": alias,
                       "policy": policy, "part": part, "status": str(log.status),
                       "samples": len(log.samples or []), "errors": errors,
                       "minutes": round((time.perf_counter() - t0) / 60, 1), **s, "smoke": smoke,
                       "log_file": Path(log.location).name if log.location else None}
                with SPEND_LOG.open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(f"{alias} / {policy} / {part}: {log.status}, {row['samples']} samples, {errors} errors, "
                      f"{row['minutes']} min | target ${s['target_usd']:.2f} judges ${s['judge_usd']:.2f}"
                      + ("" if smoke else f" | full-run total ${running:.2f}"))
                if log.status != "success":
                    sys.exit(f"stopped: {alias}/{policy}/{part} ended {log.status}. Rerun the same command; "
                             "finished calls come from the cache.")


if __name__ == "__main__":
    main()
