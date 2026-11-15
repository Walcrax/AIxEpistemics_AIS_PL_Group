"""Draw the 60 neutral vs hedge-hack reply pairs for the blind labelling check, and build the labelling page.

    python3 -I scripts/make_label_pairs.py

Rule (fixed before any label is collected):
1. Pool: the full-run Pander replies of the four targets (504 prompts each), neutral and hedge_hack, paired by
   sample_id. Sources: outputs/full_api/{neutral,hedge}_subset_results.jsonl (Grok, Kimi, exported from logs/full)
   and outputs/full_local_{mistral,qwen}/pipeline_results.jsonl.
2. 15 pairs per model. Half the pairs overall have different forced choices (FINAL) and half the same: models in
   sorted order get 8, 7, 8, 7 "differ" pairs and the rest "agree" (30 + 30).
3. rng = random.Random(20261114). Per model in sorted order: rng.sample(sorted differ ids, k), then
   rng.sample(sorted agree ids, 15 - k). Then rng.shuffle(all 60) sets the order, and for each pair in that order
   rng.random() < 0.5 puts the hedge-hack reply on side A, else on side B. Pairs are numbered L01..L60.

Writes:
- data/labels/label_pairs.json: what labellers see (pair id, claim, user prompt, reply A, reply B). No model,
  condition or FINAL answer.
- data/labels/label_key.csv: the key (pair id, model, sample_id, which side is hedge-hack, both FINALs, agree).
- data/labels/labeling_page.html: scripts/label_page_template.html with the pairs embedded, online mode (saves to
  the claude.ai page's label store).
- data/labels/labeling_offline.html: the same page in offline mode, for labellers outside the organization: labels
  stay in their browser and they send back an exported JSON file (stamped with label_pairs.json's sha256).
"""
import csv, hashlib, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED, PER_MODEL = 20261114, 15
DIFFER_QUOTA = [8, 7, 8, 7]
SOURCES = {
    "grok-4.6": ["outputs/full_api/neutral_subset_results.jsonl", "outputs/full_api/hedge_subset_results.jsonl"],
    "kimi-k3": ["outputs/full_api/neutral_subset_results.jsonl", "outputs/full_api/hedge_subset_results.jsonl"],
    "mistral-small-3.1-24b": ["outputs/full_local_mistral/pipeline_results.jsonl"],
    "qwen-3.8-27b": ["outputs/full_local_qwen/pipeline_results.jsonl"],
}
OUT = ROOT / "data" / "labels"


def load(model: str) -> dict[str, dict[str, dict]]:
    pairs: dict[str, dict[str, dict]] = {}
    for rel in SOURCES[model]:
        for line in (ROOT / rel).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("target_model") != model or r.get("dataset_kind", "subset") != "subset":
                continue
            if r.get("policy") in ("neutral", "hedge_hack"):
                pairs.setdefault(r["sample_id"], {})[r["policy"]] = r
    return {k: v for k, v in pairs.items() if len(v) == 2}


def main() -> None:
    rng = random.Random(SEED)
    chosen = []
    for model, k in zip(sorted(SOURCES), DIFFER_QUOTA):
        pairs = load(model)
        assert len(pairs) == 504, (model, len(pairs))
        differ = sorted(s for s, p in pairs.items() if p["neutral"]["final_parsed"] != p["hedge_hack"]["final_parsed"])
        agree = sorted(s for s, p in pairs.items() if p["neutral"]["final_parsed"] == p["hedge_hack"]["final_parsed"])
        for sid in rng.sample(differ, k) + rng.sample(agree, PER_MODEL - k):
            chosen.append((model, sid, pairs[sid]))
    rng.shuffle(chosen)

    shown, key = [], []
    for i, (model, sid, p) in enumerate(chosen, 1):
        pid = f"L{i:02d}"
        hedge_on_a = rng.random() < 0.5
        a, b = (p["hedge_hack"], p["neutral"]) if hedge_on_a else (p["neutral"], p["hedge_hack"])
        n = p["neutral"]
        shown.append({"id": pid, "claim": n["target"], "prompt": n["input"],
                      "a": a["response_text"], "b": b["response_text"]})
        key.append({"pair_id": pid, "model": model, "sample_id": sid, "proposition_id": n.get("proposition_id"),
                    "hedge_side": "A" if hedge_on_a else "B", "final_neutral": n["final_parsed"],
                    "final_hedge_hack": p["hedge_hack"]["final_parsed"],
                    "forced_choice_agree": n["final_parsed"] == p["hedge_hack"]["final_parsed"]})

    OUT.mkdir(parents=True, exist_ok=True)
    pairs_json = json.dumps(shown, ensure_ascii=False)
    (OUT / "label_pairs.json").write_text(json.dumps(shown, ensure_ascii=False, indent=1), encoding="utf-8")
    with (OUT / "label_key.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(key[0]))
        w.writeheader(); w.writerows(key)
    template = (ROOT / "scripts" / "label_page_template.html").read_text(encoding="utf-8")
    for token in ("__PAIRS_JSON__", "__MODE__", "__PAIRS_SHA__"):
        assert template.count(token) == 1, token
    safe = pairs_json.replace("</", "<\\/")  # keep reply text from closing the <script> element
    pairs_sha = hashlib.sha256((OUT / "label_pairs.json").read_bytes()).hexdigest()
    for mode, name in (("online", "labeling_page.html"), ("offline", "labeling_offline.html")):
        page = template.replace("__MODE__", mode).replace("__PAIRS_SHA__", pairs_sha).replace("__PAIRS_JSON__", safe)
        if mode == "offline":  # opened straight from disk, so it needs the document shell claude.ai adds online
            page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
                    'content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body style="margin:0">'
                    + page + "</body></html>")
        (OUT / name).write_text(page, encoding="utf-8")

    agree = sum(k["forced_choice_agree"] for k in key)
    print(f"{len(key)} pairs: {agree} agree, {len(key) - agree} differ; hedge on A {sum(k['hedge_side'] == 'A' for k in key)}")
    for m in sorted(SOURCES):
        print(f"  {m:24s} {sum(k['model'] == m for k in key)}")
    for f in ("label_pairs.json", "label_key.csv"):
        print(f"data/labels/{f}  sha256 {hashlib.sha256((OUT / f).read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
