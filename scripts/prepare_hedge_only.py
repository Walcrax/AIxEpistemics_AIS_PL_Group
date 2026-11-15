"""Turn hedge-only rewrites into rows that judge_local_replies.py can judge (policy "hedge_only").

    python3 -I scripts/prepare_hedge_only.py <source results.jsonl> <neutral_rewritten.jsonl> <out.jsonl>

The rewrite file (scripts/hedge_rewrite.py) keeps only sample_id, target_model and the reply text. This joins
each rewrite to its neutral source row (same target_model and sample_id, Pander subset) to get the prompt
(`input`), proposition (`target`) and metadata, replaces `response_text` with the rewritten reply and sets
policy to "hedge_only". The forced-choice fields are kept from the neutral row: the rewrite changes only the
prose, so the committed answer is the neutral one. Stops if any rewrite has no source row.
"""
import json
import sys
from pathlib import Path


def main(src: Path, rewritten: Path, out: Path) -> None:
    source = {}
    for line in src.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("policy") == "neutral" and r.get("dataset_kind", "subset") == "subset":
                source[(r["target_model"], r["sample_id"])] = r
    rows, missing = [], []
    for line in rewritten.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        w = json.loads(line)
        base = source.get((w["target_model"], w["sample_id"]))
        if base is None:
            missing.append((w["target_model"], w["sample_id"]))
            continue
        rows.append({**base, "policy": "hedge_only", "response_text": w["response_text"],
                     "original_response_text": w["original_response_text"], "rewritten": w["rewritten"],
                     "hedge_ids": w["hedge_ids"]})
    if missing:
        sys.exit(f"{len(missing)} rewrites without a neutral source row, e.g. {missing[:3]}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"{len(rows)} hedge_only rows ({sum(r['rewritten'] for r in rows)} rewritten) -> {out}")


if __name__ == "__main__":
    main(*map(Path, sys.argv[1:4]))
