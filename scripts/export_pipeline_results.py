"""Export Inspect ``.eval`` logs from ``hedge_hack_pipeline.py`` to JSONL and summary JSON.

Output JSONL rows include ``sample_id``, ``target_model``, ``response_text``, and all
Stage 2 forced-choice fields so neutral exports feed directly into ``scripts/hedge_rewrite.py``
and team analysis scripts.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from inspect_ai.log import EvalLog, read_eval_log

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
_STAGE2_METADATA_KEYS = {
    "policy",
    "commitment_type",
    "valid_options",
    "stage1_completion",
    "stage1_usage",
    "stage2_prompt",
    "stage2_raw",
    "stage2_retry_used",
    "stage2_retry_raw",
    "final_parsed",
    "final_parse_reason",
    "dataset_kind",
}


def _infer_target_model(log: EvalLog) -> str:
    meta = getattr(log.eval, "metadata", None) or {}
    if meta.get("target_model"):
        return str(meta["target_model"])
    raw = str(getattr(log.eval, "model", "") or "")
    for prefix in ("ollama/",):
        if raw.startswith(prefix):
            raw = raw[len(prefix) :]
    if raw == "qwen-sprint":
        return "qwen-3.8-27b"
    if raw == "mistral-sprint":
        return "mistral-small-3.1-24b"
    return raw


def extract_rows_from_log(log: EvalLog, *, log_path: Path | None = None) -> list[dict[str, Any]]:
    """Extract normalized per-sample records from a single Inspect ``EvalLog``."""
    target_model = _infer_target_model(log)
    task_args = getattr(log.eval, "task_args", None) or {}
    task_policy = task_args.get("policy")
    rows: list[dict[str, Any]] = []

    for sample in log.samples or []:
        meta = sample.metadata or {}
        score_obj = (sample.scores or {}).get("final_commitment_scorer")
        score_meta = (score_obj.metadata if score_obj else None) or {}
        stage1_text = meta.get("stage1_completion")
        if stage1_text is None and sample.output is not None:
            stage1_text = sample.output.completion

        policy = meta.get("policy") or score_meta.get("policy") or task_policy
        is_known = bool(
            meta.get("options")
            or meta.get("source") == "sycobench-600"
            or meta.get("dataset_kind") == "known"
        )
        rows.append(
            {
                "id": str(sample.id),
                "sample_id": str(sample.id),
                "target_model": target_model,
                "policy": policy,
                "dataset_kind": meta.get("dataset_kind") or ("known" if is_known else "subset"),
                "commitment_type": meta.get("commitment_type")
                or ("known_item" if is_known else "pander_proposition"),
                "proposition_id": meta.get("proposition_id"),
                "proposition": meta.get("proposition"),
                "prior": meta.get("prior"),
                "domain": meta.get("domain"),
                "in_4_2_4": meta.get("in_4_2_4"),
                "question_id": meta.get("question_id"),
                "difficulty": meta.get("difficulty"),
                "asserted_wrong": meta.get("asserted_wrong"),
                "target": str(sample.target),
                "input": str(sample.input),
                "response_text": stage1_text or "",
                "metadata": {k: v for k, v in meta.items() if k not in _STAGE2_METADATA_KEYS},
                "valid_options": meta.get("valid_options"),
                "stage2_raw": meta.get("stage2_raw"),
                "stage2_retry_used": bool(meta.get("stage2_retry_used", False)),
                "stage2_retry_raw": meta.get("stage2_retry_raw"),
                "final_parsed": meta.get("final_parsed"),
                "final_parse_reason": meta.get("final_parse_reason"),
                "known_correct": score_meta.get("known_correct") if is_known else None,
                "stage1_usage": meta.get("stage1_usage"),
                "log_file": log_path.name if log_path else (
                    Path(log.location).name if getattr(log, "location", None) else None
                ),
            }
        )
    return rows


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate parse rate, true rate, retry rate, and known-item accuracy by run slice."""
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row.get("target_model") or "unknown"),
            str(row.get("policy") or "unknown"),
            str(row.get("dataset_kind") or "unknown"),
        )
        grouped[key].append(row)

    summary: list[dict[str, Any]] = []
    for (target_model, policy, dataset_kind), group in sorted(grouped.items()):
        n = len(group)
        parsed_rows = [r for r in group if r.get("final_parsed") is not None]
        retry_rows = [r for r in group if r.get("stage2_retry_used")]
        reasons = Counter(str(r.get("final_parse_reason") or "unknown") for r in group)

        entry: dict[str, Any] = {
            "target_model": target_model,
            "policy": policy,
            "dataset_kind": dataset_kind,
            "samples": n,
            "parsed": len(parsed_rows),
            "final_parse_rate": round(len(parsed_rows) / n, 4) if n else 0.0,
            "retries": len(retry_rows),
            "parse_reasons": dict(sorted(reasons.items())),
        }
        if dataset_kind == "known":
            correct = sum(1 for r in group if r.get("known_correct"))
            entry["known_correct"] = correct
            entry["known_accuracy"] = round(correct / n, 4) if n else 0.0
        else:
            trues = sum(1 for r in group if r.get("final_parsed") == "TRUE")
            falses = sum(1 for r in group if r.get("final_parsed") == "FALSE")
            entry["true_count"] = trues
            entry["false_count"] = falses
            entry["true_rate"] = round(trues / n, 4) if n else 0.0
        summary.append(entry)
    return summary


def resolve_log_paths(inputs: list[Path]) -> list[Path]:
    """Expand ``.eval`` files and directories cleanly in chronological/name order."""
    paths: list[Path] = []
    for item in inputs:
        if item.is_dir():
            paths.extend(sorted(item.rglob("*.eval")))
        elif item.is_file():
            paths.append(item)
        else:
            raise FileNotFoundError(f"Log path not found: {item}")
    return list(dict.fromkeys(paths))


def export_eval_logs(
    inputs: list[Path],
    *,
    out_jsonl: Path,
    rewrite_jsonl: Path | None = None,
    rewritten_jsonl: Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read Inspect ``.eval`` logs and write normalized JSONL (and optional rewrite files)."""
    log_paths = resolve_log_paths(inputs)
    all_rows: list[dict[str, Any]] = []
    for path in log_paths:
        log = read_eval_log(str(path))
        all_rows.extend(extract_rows_from_log(log, log_path=path))

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for row in all_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    if rewrite_jsonl is not None or rewritten_jsonl is not None:
        neutral_subset = [
            r
            for r in all_rows
            if r.get("policy") == "neutral" and r.get("dataset_kind") == "subset"
        ]
        target_rewrite_in = rewrite_jsonl or (
            rewritten_jsonl.with_name("neutral_for_rewrite.jsonl") if rewritten_jsonl else None
        )
        if target_rewrite_in is not None:
            target_rewrite_in.parent.mkdir(parents=True, exist_ok=True)
            with target_rewrite_in.open("w", encoding="utf-8") as fh:
                for r in neutral_subset:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            if rewritten_jsonl is not None and neutral_subset:
                if str(SCRIPTS_DIR) not in sys.path:
                    sys.path.insert(0, str(SCRIPTS_DIR))
                import hedge_rewrite  # type: ignore

                rewritten_jsonl.parent.mkdir(parents=True, exist_ok=True)
                with contextlib.redirect_stdout(io.StringIO()):
                    hedge_rewrite.main(target_rewrite_in, rewritten_jsonl)

    return all_rows, summarize_rows(all_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export hedge_hack_pipeline Inspect .eval logs to JSONL and print metrics."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Inspect .eval file(s) or directories containing .eval logs.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "pipeline_results.jsonl",
        help="Destination JSONL path for all extracted sample rows.",
    )
    parser.add_argument(
        "--rewrite-out",
        type=Path,
        default=None,
        help="Optional JSONL filtered to neutral proposition replies ready for scripts/hedge_rewrite.py.",
    )
    parser.add_argument(
        "--rewritten-out",
        type=Path,
        default=None,
        help="Optional hedge-only rewritten JSONL produced via scripts/hedge_rewrite.py.",
    )
    args = parser.parse_args(argv)

    rows, summary = export_eval_logs(
        args.inputs,
        out_jsonl=args.out,
        rewrite_jsonl=args.rewrite_out,
        rewritten_jsonl=args.rewritten_out,
    )
    print(json.dumps({"rows_exported": len(rows), "out": str(args.out), "summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
