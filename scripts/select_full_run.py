"""Pick the 42-proposition full-run set: the 5 pilot propositions plus 37 more, 7 per domain.

    python3 -I scripts/select_full_run.py

Rule (fixed before any full-run result):
1. Pool: the 60 propositions of data/subset (6 domains x 10).
2. Domain quotas: 7 per domain (6 domains x 7 = 42). (If TOTAL is not a multiple of 6, the domains that get one
   extra are drawn with rng.sample(sorted(domains), remainder); with 42 there is no remainder and no draw.)
3. The 5 pilot propositions (data/pilot/pilot_prompts.jsonl) are kept and count towards their domain's quota.
4. Each domain is filled to its quota with rng.sample(sorted(remaining ids in that domain), needed), domains in
   sorted order, rng = random.Random(20261114).
Every proposition keeps all 12 of its subset prompts (4 skeptic, 4 neutral, 4 believer).

Writes data/full_run/full_run_propositions.csv (42 rows, the subset's columns plus `in_pilot`) and
data/full_run/full_run_prompts.jsonl (504 subset rows, unchanged), and prints their SHA-256.
"""
import csv, hashlib, json, random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED, TOTAL = 20261114, 42
SUBSET = ROOT / "data" / "subset"
PILOT = ROOT / "data" / "pilot" / "pilot_prompts.jsonl"
OUT = ROOT / "data" / "full_run"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    with (SUBSET / "selected_propositions.csv").open(newline="", encoding="utf-8") as fh:
        props = list(csv.DictReader(fh))
    pilot = {json.loads(l)["metadata"]["proposition_id"] for l in PILOT.read_text().splitlines() if l.strip()}
    by_domain: dict[str, list[str]] = {}
    for p in props:
        by_domain.setdefault(p["domain"], []).append(p["proposition_id"])
    domains = sorted(by_domain)
    assert pilot <= {p["proposition_id"] for p in props}, "pilot propositions must come from the subset"

    rng = random.Random(SEED)
    base, extra = divmod(TOTAL, len(domains))
    quota = {d: base for d in domains}
    for d in rng.sample(domains, extra):
        quota[d] += 1

    chosen = set(pilot)
    for d in domains:
        have = [p for p in by_domain[d] if p in pilot]
        rest = sorted(p for p in by_domain[d] if p not in pilot)
        need = quota[d] - len(have)
        assert 0 <= need <= len(rest), (d, need)
        chosen.update(rng.sample(rest, need))
    assert len(chosen) == TOTAL

    OUT.mkdir(parents=True, exist_ok=True)
    rows = [{**p, "in_pilot": p["proposition_id"] in pilot} for p in props if p["proposition_id"] in chosen]
    prop_path = OUT / "full_run_propositions.csv"
    with prop_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(props[0].keys()) + ["in_pilot"])
        w.writeheader()
        w.writerows(rows)
    lines = [l for l in (SUBSET / "selected_prompts.jsonl").read_text(encoding="utf-8").splitlines()
             if l.strip() and json.loads(l)["metadata"]["proposition_id"] in chosen]
    prompt_path = OUT / "full_run_prompts.jsonl"
    prompt_path.write_text("".join(l + "\n" for l in lines), encoding="utf-8")

    counts = Counter(r["domain"] for r in rows)
    priors = Counter(json.loads(l)["metadata"]["prior"] for l in lines)
    print(f"{len(rows)} propositions ({sum(r['in_pilot'] for r in rows)} pilot), {len(lines)} prompts")
    for d in domains:
        print(f"  {d:26s} {counts[d]}  (pilot {sum(1 for r in rows if r['domain'] == d and r['in_pilot'])})")
    print(f"  priors: {dict(priors)}")
    print(f"{prop_path.relative_to(ROOT)}  sha256 {sha256(prop_path)}")
    print(f"{prompt_path.relative_to(ROOT)}  sha256 {sha256(prompt_path)}")


if __name__ == "__main__":
    main()
