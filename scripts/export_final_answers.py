"""Export per-prompt forced-choice (FINAL:) answers from pilot runs, for the H2 noise floor.

    uv run --project external/pander-score python -I scripts/export_final_answers.py \
        run1=logs/pilot_run1 run2=logs/pilot [--out data/pilot/final_answers.csv]

Each argument is label=log dir, in run order. A log already listed under an earlier label is skipped, so a
later dir that still holds earlier logs only contributes its new runs. Only full pilot runs are kept
(metadata stage "pilot", 60 samples, status success); the 12-prompt smoke tests are dropped. If one dir holds
two full runs of the same model and policy, the export stops rather than guess.

Long format, one row per run x model x policy x prompt: run, model, policy, sample_id, proposition_id,
prior, final_parsed (TRUE / FALSE / empty if unparsed), final_parse_reason, stage2_retry_used, log_file.
"""
import argparse, csv, sys
from pathlib import Path

from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parent.parent
FULL_SAMPLES = 60
COLS = ["run", "model", "policy", "sample_id", "proposition_id", "prior", "final_parsed",
        "final_parse_reason", "stage2_retry_used", "log_file"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="label=log dir, in run order")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "pilot" / "final_answers.csv")
    a = ap.parse_args()
    seen, rows = set(), []
    for spec in a.runs:
        label, _, d = spec.partition("=")
        picked: dict[tuple[str, str], Path] = {}
        for p in sorted(Path(d).glob("*.eval")):
            if p.name in seen:
                continue
            h = read_eval_log(str(p), header_only=True)
            meta = h.eval.metadata or {}
            if meta.get("stage") != "pilot" or h.status != "success" or h.eval.dataset.samples != FULL_SAMPLES:
                continue
            key = (meta["target_model"], meta["policy"])
            if key in picked:
                sys.exit(f"{label}: two full runs of {key} ({picked[key].name}, {p.name})")
            picked[key] = p
        for (model, policy), p in sorted(picked.items()):
            seen.add(p.name)
            for s in read_eval_log(str(p)).samples:
                m = s.metadata or {}
                rows.append({"run": label, "model": model, "policy": policy, "sample_id": s.id,
                             "proposition_id": m.get("proposition_id"), "prior": m.get("prior"),
                             "final_parsed": m.get("final_parsed") or "",
                             "final_parse_reason": m.get("final_parse_reason"),
                             "stage2_retry_used": bool(m.get("stage2_retry_used")), "log_file": p.name})
        print(f"{label}: {', '.join(f'{k[0]}/{k[1]}' for k in sorted(picked)) or 'no full runs'}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["model"], r["policy"], r["sample_id"], r["run"])))
    print(f"{len(rows)} rows -> {a.out.relative_to(ROOT) if a.out.is_relative_to(ROOT) else a.out}")


if __name__ == "__main__":
    main()
