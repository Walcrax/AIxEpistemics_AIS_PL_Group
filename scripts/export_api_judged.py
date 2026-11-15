"""Export the API full-run logs (Grok 4.6, Kimi K3) for scripts/analysis.py: judge fields included.

    uv run --project external/pander-score python -I scripts/export_api_judged.py [log dir]

Reads the successful logs with metadata stage "full" in logs/full (one per model x part x policy, as
api_full_scores.py) and writes, with no model or judge calls:

- outputs/full_api/judged.jsonl: Pander-subset rows, both policies, in the same schema as
  outputs/full_local_*/judged.jsonl (pipeline fields plus judge1_*/judge2_* from credence_scorer).
- outputs/full_api/known_results.jsonl: known-item rows, both policies (known_correct, final_parsed).
"""
import json
import sys
from pathlib import Path

from inspect_ai.log import read_eval_log

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_pipeline_results import ROOT, extract_rows_from_log  # noqa: E402

FIELDS = ("llm_id", "refusal", "informative", "credence", "explanation", "raw_completion")


def main() -> None:
    log_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "logs" / "full"
    logs: dict[tuple[str, str, str], Path] = {}
    for p in sorted(log_dir.glob("*.eval")):
        h = read_eval_log(str(p), header_only=True)
        m = h.eval.metadata or {}
        if h.status != "success" or m.get("stage") != "full":
            continue
        key = (m["target_model"], m["part"], m["policy"])
        if key in logs:
            sys.exit(f"two successful logs for {key}: {logs[key].name}, {p.name}")
        logs[key] = p
    if len(logs) != 8:
        sys.exit(f"expected 8 logs (2 models x 2 parts x 2 policies), found {len(logs)}: {sorted(logs)}")

    subset, known = [], []
    for (model, part, policy), p in sorted(logs.items()):
        log = read_eval_log(str(p))
        rows = extract_rows_from_log(log, log_path=p)
        by_id = {str(s.id): s for s in log.samples or []}
        for r in rows:
            r["target_model"], r["policy"] = model, policy
            if part == "subset":
                cred = (by_id[r["sample_id"]].scores or {}).get("credence_scorer")
                cm = (cred.metadata if cred else None) or {}
                for i in (1, 2):
                    r.update({f"judge{i}_{f}": cm.get(f"judge{i}_{f}") for f in FIELDS})
                subset.append(r)
            else:
                known.append(r)
        print(f"{model:9s} {part:6s} {policy:10s} {len(rows)} rows  <- {p.name}")

    out = ROOT / "outputs" / "full_api"
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("judged.jsonl", subset), ("known_results.jsonl", known)):
        (out / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(f"-> outputs/full_api/{name} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
