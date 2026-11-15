"""Blind labelling check: Cohen's kappa and the "often differ" threshold (data/labels/README.md).

    python3 -I scripts/label_agreement.py data/labels/label_key.csv data/labels/label_pairs.json \
        data/labels/hedgehack_labels_<a>.json data/labels/hedgehack_labels_<b>.json

Each label file must carry the pairs_sha256 of label_pairs.json and label all 60 pairs (v in same / different /
unclear). Writes outputs/labels/agreement.{json,md}. Standard library only.

- Kappa: Cohen's kappa on the three labels, and on Same vs Different with pairs either labeller marked Can't tell
  dropped.
- Different share: per labeller, Different / (Same + Different), Can't tell excluded; the mean of the two labellers.
  Overall, by forced-choice agreement and by model.
- Threshold: the mean Different share on the 30 forced-choice-agree pairs; >= 20% means conclusions "often differ"
  and H2 fails as stated. 95% interval from 2,000 bootstrap draws of pairs (seed 20261114).
"""
import csv
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABELS = ("same", "different", "unclear")
THRESHOLD = 0.20
SEED, DRAWS = 20261114, 2000


def kappa(a: list[str], b: list[str], cats) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return None if pe == 1 else (po - pe) / (1 - pe)


def diff_share(labels: list[str]) -> float | None:
    s, d = labels.count("same"), labels.count("different")
    return None if s + d == 0 else d / (s + d)


def mean_share(rows, names) -> float | None:
    shares = [diff_share([r[n] for r in rows]) for n in names]
    shares = [x for x in shares if x is not None]
    return sum(shares) / len(shares) if shares else None


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.0f}%"


def main() -> None:
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    key_p, pairs_p, *label_ps = map(Path, sys.argv[1:])
    sha = hashlib.sha256(pairs_p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    with key_p.open(newline="", encoding="utf-8") as f:
        key = {r["pair_id"]: r for r in csv.DictReader(f)}

    names, files = [], []
    for p in label_ps:
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("pairs_sha256") != sha:
            sys.exit(f"{p}: pairs_sha256 does not match {pairs_p}")
        lab = {k: v["v"] for k, v in d["labels"].items()}
        if set(lab) != set(key) or any(v not in LABELS for v in lab.values()):
            sys.exit(f"{p}: must label every pair in {key_p} with one of {LABELS}")
        names.append(d["labeller"])
        files.append(lab)

    rows = [{"pair_id": k, "model": key[k]["model"], "agree": key[k]["forced_choice_agree"] == "True",
             **{n: f[k] for n, f in zip(names, files)}} for k in sorted(key)]
    a, b = ([r[n] for r in rows] for n in names)
    both = [(x, y) for x, y in zip(a, b) if "unclear" not in (x, y)]

    groups = {"all": rows, "forced choices agree": [r for r in rows if r["agree"]],
              "forced choices differ": [r for r in rows if not r["agree"]]}
    groups |= {m: [r for r in rows if r["model"] == m] for m in sorted({r["model"] for r in rows})}
    table = {g: {"n": len(rs), **{n: {c: [r[n] for r in rs].count(c) for c in LABELS} for n in names},
                 **{f"different_share_{n}": diff_share([r[n] for r in rs]) for n in names},
                 "different_share_mean": mean_share(rs, names),
                 "kappa_3": kappa([r[names[0]] for r in rs], [r[names[1]] for r in rs], LABELS),
                 "raw_agreement": sum(r[names[0]] == r[names[1]] for r in rs) / len(rs)}
             for g, rs in groups.items()}

    agree = groups["forced choices agree"]
    rng = random.Random(SEED)
    boot = sorted(x for x in (mean_share([rng.choice(agree) for _ in agree], names) for _ in range(DRAWS))
                  if x is not None)
    ci = (boot[int(0.025 * len(boot))], boot[int(0.975 * len(boot)) - 1])
    stat = table["forced choices agree"]["different_share_mean"]
    res = {
        "labellers": names, "pairs_sha256": sha, "n_pairs": len(rows),
        "kappa_3": kappa(a, b, LABELS), "raw_agreement_3": table["all"]["raw_agreement"],
        "kappa_same_vs_different": kappa([x for x, _ in both], [y for _, y in both], LABELS[:2]),
        "n_same_vs_different": len(both),
        "threshold": {"rule": "mean Different share on forced-choice-agree pairs >= 20%", "value": stat,
                      "ci95": ci, "often_differ": stat is not None and stat >= THRESHOLD},
        "groups": table,
    }

    out = ROOT / "outputs" / "labels"
    out.mkdir(parents=True, exist_ok=True)
    (out / "agreement.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    k2 = res["kappa_same_vs_different"]
    md = [f"# Blind labelling: {names[0]} and {names[1]}, {len(rows)} pairs", "",
          f"- Cohen's kappa, three labels: {res['kappa_3']:.2f} (raw agreement {pct(res['raw_agreement_3'])})",
          f"- Cohen's kappa, Same vs Different ({len(both)} pairs neither marked Can't tell): "
          + ("n/a" if k2 is None else f"{k2:.2f}"),
          f"- Threshold: mean Different share on the {len(agree)} forced-choice-agree pairs = {pct(stat)} "
          f"[{pct(ci[0])}, {pct(ci[1])}]; often differ (>= 20%): {res['threshold']['often_differ']}", "",
          "| group | n | " + " | ".join(f"{n} S/D/?" for n in names) + " | Different share (mean) | kappa |",
          "|---|---|" + "---|" * len(names) + "---|---|"]
    for g, t in table.items():
        cells = " | ".join(f"{t[n]['same']}/{t[n]['different']}/{t[n]['unclear']}" for n in names)
        kk = "n/a" if t["kappa_3"] is None else f"{t['kappa_3']:.2f}"
        md.append(f"| {g} | {t['n']} | {cells} | {pct(t['different_share_mean'])} | {kk} |")
    (out / "agreement.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
