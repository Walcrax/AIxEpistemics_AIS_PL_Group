"""Hedge-only control: add the hedge-hack style to neutral replies without changing anything else.

    uv run --project external/pander-score python -I scripts/hedge_rewrite.py <neutral replies> <out.jsonl>

Input: a JSONL file, or a Parquet file such as a Pander per-model export, with one row per reply and
at least `sample_id` and `response_text` (`target_model` is kept if present).

Each reply is kept word for word. The script puts one opener sentence before it and one both-sides
sentence plus one offer-to-abstain sentence after it, all drawn from prompts/hedge_bank.json. The
choice is a stable hash of (target_model, sample_id, slot), so reruns give identical output and the
sentences are spread evenly across replies. Empty or missing replies are passed through unchanged
and flagged, so the judge sees them exactly as it saw the original.

Output JSONL, one row per input row: sample_id, target_model, response_text (rewritten),
original_response_text, rewritten (bool), hedge_ids (bank index per slot).
"""
import hashlib
import json
import sys
from pathlib import Path

SLOTS = ("opener", "both_sides", "abstain")
BANK_PATH = Path(__file__).resolve().parent.parent / "prompts" / "hedge_bank.json"


def load_bank(path: Path = BANK_PATH) -> dict[str, list[str]]:
    bank = json.loads(path.read_text(encoding="utf-8"))
    return {slot: bank[slot] for slot in SLOTS}


def pick(bank: dict[str, list[str]], model: str, sample_id: str) -> dict[str, int]:
    ids = {}
    for slot in SLOTS:
        h = hashlib.sha256(f"{model}|{sample_id}|{slot}".encode()).digest()
        ids[slot] = int.from_bytes(h[:8], "big") % len(bank[slot])
    return ids


def rewrite(text: str, bank: dict[str, list[str]], ids: dict[str, int]) -> str:
    body = text.strip("\n")
    closing = f"{bank['both_sides'][ids['both_sides']]} {bank['abstain'][ids['abstain']]}"
    return f"{bank['opener'][ids['opener']]}\n\n{body}\n\n{closing}"


def read_rows(path: Path) -> list[dict]:
    if path.suffix == ".parquet":
        import polars as pl  # only needed for Parquet input
        return pl.read_parquet(path).to_dicts()
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main(in_path: Path, out_path: Path) -> None:
    bank = load_bank()
    rows = read_rows(in_path)
    n_done = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for r in rows:
            text, model = r.get("response_text"), r.get("target_model") or ""
            ok = isinstance(text, str) and text.strip() != ""
            ids = pick(bank, model, r["sample_id"]) if ok else None
            new = rewrite(text, bank, ids) if ok else text
            if ok:
                assert text.strip("\n") in new  # the original reply survives word for word
                n_done += 1
            out.write(json.dumps({
                "sample_id": r["sample_id"], "target_model": model, "response_text": new,
                "original_response_text": text, "rewritten": ok, "hedge_ids": ids,
            }, ensure_ascii=False) + "\n")
    print(f"rewrote {n_done} of {len(rows)} replies -> {out_path}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
