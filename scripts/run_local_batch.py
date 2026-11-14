"""Batched Inspect runner for local Ollama models (Task 3) and two-stage evaluation (Task 4).

Processes one model at a time so the full model + KV cache stays 100% resident in 16 GB VRAM
(preventing slow CPU spill / model reload thrashing), while running all policies and concurrent
batches (`max_connections`, default 4 from ``configs/models.yaml``) while that model is hot.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from inspect_ai import eval as inspect_eval
from inspect_ai.model import GenerateConfig

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from export_pipeline_results import export_eval_logs, summarize_rows  # noqa: E402
from hedge_hack_pipeline import (  # noqa: E402
    SUBSET_PATH,
    DatasetKind,
    PolicyName,
    _normalize_proposition_ids,
    hedge_hack_eval,
    write_pilot_slice,
)
from local_models import (  # noqa: E402
    list_local_targets,
    normalize_local_alias,
    resolve_target_model,
)


def _expand_models(model_args: list[str] | None) -> list[str]:
    if not model_args or model_args == ["all"] or "all" in model_args:
        return list_local_targets()
    resolved: list[str] = []
    for raw in model_args:
        try:
            resolved.append(normalize_local_alias(raw))
        except KeyError:
            resolved.append(raw)
    return list(dict.fromkeys(resolved))


def _expand_policies(policy_arg: str) -> list[PolicyName]:
    if policy_arg == "both":
        return ["neutral", "hedge_hack"]
    if policy_arg in ("neutral", "hedge_hack"):
        return [policy_arg]  # type: ignore[list-item]
    raise ValueError(f"Unsupported --policy {policy_arg!r}")


def _extract_metrics_dict(eval_log: Any) -> dict[str, float]:
    out: dict[str, float] = {}
    results = getattr(eval_log, "results", None)
    if not results or not getattr(results, "scores", None):
        return out
    for eval_score in results.scores:
        prefix = eval_score.name
        for metric_name, metric_obj in (eval_score.metrics or {}).items():
            out[f"{prefix}.{metric_name}"] = round(float(metric_obj.value), 4)
    return out


def run_batch(
    *,
    models: list[str],
    policies: list[PolicyName],
    dataset: str,
    subset_path: Path | None = None,
    known_path: Path | None = None,
    only_4_2_4: bool,
    props: int | None = None,
    proposition_ids: list[str] | str | None = None,
    limit: int | None,
    max_connections: int | None,
    max_tokens: int | None,
    fc_max_tokens: int | None,
    with_judges: bool,
    use_base: bool,
    log_dir: Path | None,
    export_dir: Path | None,
    no_export: bool = False,
    stage: str | None = None,
    fail_on_error: float | bool,
    display: str,
) -> dict[str, Any]:
    """Execute batched evaluations sequentially across *models* and *policies*."""
    if props is not None and proposition_ids is not None:
        raise ValueError("Pass either --props or --proposition-ids, not both.")
    if (props is not None or proposition_ids is not None) and dataset in ("smoke", "known"):
        raise ValueError("--props and --proposition-ids require --dataset subset (or both).")

    is_pilot = stage == "pilot" or props is not None or proposition_ids is not None or subset_path is not None
    effective_stage = stage or ("smoke" if dataset == "smoke" else ("pilot" if is_pilot else "batch"))
    resolved_log_dir = log_dir or (ROOT / "logs" / ("pilot_local" if is_pilot else ""))
    resolved_export_dir = (
        None
        if no_export
        else (export_dir or (ROOT / "outputs" / ("pilot_local" if is_pilot else "local_batch")))
    )

    ds_kind: DatasetKind = "both" if dataset == "smoke" else dataset  # type: ignore[assignment]
    effective_limit = (2 if limit is None else limit) if dataset == "smoke" else limit

    effective_subset_path = subset_path or SUBSET_PATH
    picked_ids = _normalize_proposition_ids(proposition_ids)
    slice_file: Path | None = None
    if props is not None or picked_ids is not None:
        slice_dir = resolved_export_dir or resolved_log_dir
        slice_file, picked_ids = write_pilot_slice(
            slice_dir / "pilot_prompts.jsonl",
            n_props=props,
            proposition_ids=picked_ids,
            subset_path=effective_subset_path,
        )
        effective_subset_path = slice_file

    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    log_paths: list[Path] = []
    run_summaries: list[dict[str, Any]] = []

    for alias in models:
        override = GenerateConfig(max_tokens=max_tokens) if max_tokens is not None else None
        model_obj, info = resolve_target_model(alias, config=override, use_base=use_base)
        conc = max_connections or int(info.get("max_connections") or 4)
        canonical = str(info["canonical_alias"])

        for policy in policies:
            task = hedge_hack_eval(
                policy=policy,
                dataset=ds_kind,
                subset_path=str(effective_subset_path),
                known_path=str(known_path) if known_path else None,
                only_4_2_4=only_4_2_4,
                limit=effective_limit,
                fc_max_tokens=fc_max_tokens,
                with_judges=with_judges,
            )
            t0 = time.perf_counter()
            eval_logs = inspect_eval(
                task,
                model=model_obj,
                max_connections=conc,
                log_dir=str(resolved_log_dir),
                display=display,  # type: ignore[arg-type]
                fail_on_error=fail_on_error,
                metadata={
                    "target_model": canonical,
                    "policy": policy,
                    "dataset": dataset,
                    "stage": effective_stage,
                    "only_4_2_4": only_4_2_4,
                    "proposition_ids": picked_ids,
                    "max_connections": conc,
                },
            )
            elapsed = round(time.perf_counter() - t0, 2)
            for elog in eval_logs:
                loc = Path(elog.location) if getattr(elog, "location", None) else None
                if loc is not None:
                    log_paths.append(loc)
                run_summaries.append(
                    {
                        "target_model": canonical,
                        "policy": policy,
                        "dataset": dataset,
                        "stage": effective_stage,
                        "status": str(elog.status),
                        "samples": len(elog.samples or []),
                        "max_connections": conc,
                        "elapsed_s": elapsed,
                        "metrics": _extract_metrics_dict(elog),
                        "log_file": str(loc) if loc else None,
                    }
                )
                if elog.status != "success":
                    raise RuntimeError(
                        f"Inspect eval ended with status={elog.status!r} for "
                        f"{canonical}/{policy}: {getattr(elog, 'error', None)}"
                    )

    payload: dict[str, Any] = {
        "stage": effective_stage,
        "proposition_ids": picked_ids,
        "pilot_slice_path": str(slice_file) if slice_file else None,
        "runs": run_summaries,
    }
    if resolved_export_dir is not None and log_paths:
        resolved_export_dir.mkdir(parents=True, exist_ok=True)
        out_jsonl = resolved_export_dir / "pipeline_results.jsonl"
        rewrite_jsonl = resolved_export_dir / "neutral_for_rewrite.jsonl"
        rewritten_jsonl = resolved_export_dir / "neutral_rewritten.jsonl"
        rows, agg = export_eval_logs(
            log_paths,
            out_jsonl=out_jsonl,
            rewrite_jsonl=rewrite_jsonl,
            rewritten_jsonl=rewritten_jsonl,
        )
        summary_path = resolved_export_dir / "summary.json"
        summary_data = {
            "stage": effective_stage,
            "proposition_ids": picked_ids,
            "runs": run_summaries,
            "aggregate": agg,
        }
        summary_path.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
        payload["exported_rows"] = len(rows)
        payload["export_jsonl"] = str(out_jsonl)
        payload["rewrite_jsonl"] = str(rewrite_jsonl)
        if rewritten_jsonl.exists():
            payload["rewritten_jsonl"] = str(rewritten_jsonl)
        payload["aggregate"] = agg
    elif log_paths:
        rows = []
        from inspect_ai.log import read_eval_log
        from export_pipeline_results import extract_rows_from_log

        for p in log_paths:
            rows.extend(extract_rows_from_log(read_eval_log(str(p)), log_path=p))
        payload["aggregate"] = summarize_rows(rows)

    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run batched two-stage Inspect evaluations on local Ollama models."
    )
    parser.add_argument(
        "--model",
        nargs="+",
        default=["all"],
        help="Target alias(es): qwen-3.8-27b, mistral-small-3.1-24b, API aliases, or 'all'.",
    )
    parser.add_argument(
        "--policy",
        choices=["neutral", "hedge_hack", "both"],
        default="both",
        help="System prompt condition(s) to evaluate.",
    )
    parser.add_argument(
        "--dataset",
        choices=["subset", "known", "both", "smoke"],
        default="subset",
        help="Dataset slice ('smoke' runs 2 subset + 2 known items per model/policy).",
    )
    parser.add_argument(
        "--subset-path",
        type=Path,
        default=None,
        help="Pander prompts JSONL to use instead of data/subset/selected_prompts.jsonl "
        "(pilot: data/pilot/pilot_prompts.jsonl).",
    )
    parser.add_argument(
        "--known-path",
        type=Path,
        default=None,
        help="Custom known-items JSONL path (defaults to data/known_items/known_items.jsonl).",
    )
    parser.add_argument(
        "--props",
        type=int,
        default=None,
        help="Draw N domain-spread propositions matching run_api_pilot.pilot_slice (seed 20261114).",
    )
    parser.add_argument(
        "--proposition-ids",
        nargs="+",
        default=None,
        help="Filter subset to exact proposition IDs (space- or comma-separated).",
    )
    parser.add_argument(
        "--only-4-2-4",
        action="store_true",
        help="Restrict Pander subset to the Stage A in_4_2_4 slice.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Cap samples per dataset.")
    parser.add_argument(
        "--max-connections",
        type=int,
        default=None,
        help="Override concurrent Inspect sample requests (default: model config in models.yaml).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Override Stage 1 max_tokens (default: 2048 for local models).",
    )
    parser.add_argument(
        "--fc-max-tokens",
        type=int,
        default=None,
        help="Override Stage 2 forced-choice max_tokens.",
    )
    parser.add_argument(
        "--with-judges",
        action="store_true",
        help="Attach Pander credence_scorer judges (requires external/pander-score + judge API keys).",
    )
    parser.add_argument(
        "--use-base",
        action="store_true",
        help="Use raw Ollama base_model tags instead of models/Modelfile.* aliases.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Directory for Inspect .eval logs (defaults to logs/pilot_local for pilot runs, else logs).",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=None,
        help="Directory for exported JSONL, rewrites, and summary JSON (defaults to outputs/pilot_local for pilot runs).",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip exporting JSONL files after evaluation.",
    )
    parser.add_argument(
        "--stage",
        default=None,
        help="Optional stage tag stored in Inspect eval metadata (e.g. 'pilot', 'batch').",
    )
    parser.add_argument(
        "--fail-on-error",
        type=float,
        default=0.05,
        help="Sample failure tolerance passed to inspect_ai.eval (default 0.05; 0 fails immediately).",
    )
    parser.add_argument(
        "--display",
        choices=["plain", "none", "rich"],
        default="plain",
        help="Inspect console display mode.",
    )
    args = parser.parse_args(argv)

    result = run_batch(
        models=_expand_models(args.model),
        policies=_expand_policies(args.policy),
        dataset=args.dataset,
        subset_path=args.subset_path,
        known_path=args.known_path,
        only_4_2_4=args.only_4_2_4,
        props=args.props,
        proposition_ids=args.proposition_ids,
        limit=args.limit,
        max_connections=args.max_connections,
        max_tokens=args.max_tokens,
        fc_max_tokens=args.fc_max_tokens,
        with_judges=args.with_judges,
        use_base=args.use_base,
        log_dir=args.log_dir,
        export_dir=args.export_dir,
        no_export=args.no_export,
        stage=args.stage,
        fail_on_error=args.fail_on_error,
        display=args.display,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
