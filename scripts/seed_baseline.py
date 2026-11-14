"""Check whether our seeded draw is typical: rerun select_propositions.py with seeds 0-99 and compare
each draw's scores on the 18 published models with the full 6-domain scores (mean gap, mean and max
absolute gap, Spearman rank correlation). Writes scratch output under /tmp. Zero API calls.

    uv run --project external/pander-score python -I scripts/seed_baseline.py . <hf v1/benchmark dir>
"""
import sys, glob, os
from pathlib import Path
import numpy as np, polars as pl
from scipy.stats import spearmanr
sys.path.insert(0, sys.argv[1] + "/scripts")
import select_propositions as sp
from check_subset_scores import score
root = Path(sys.argv[2])
attrs = pl.read_parquet(root / "prompt_attributes.parquet"); scr = sp.screen(attrs)
prompts = scr.select(["sample_id", "proposition_id", "domain", "valence"])
models = {}
for f in sorted((root / "per_model").glob("*.parquet")):
    m = pl.read_parquet(f, columns=["sample_id","published_condition","judge1_credence","judge2_credence","judge1_informative","judge2_informative"])
    c1, c2 = pl.col("judge1_credence"), pl.col("judge2_credence")
    ok = pl.col("published_condition") & c1.is_not_null() & c2.is_not_null() & pl.col("judge1_informative").fill_null(False) & pl.col("judge2_informative").fill_null(False) & ((c1-c2).abs() <= 0.2+1e-9)
    d = prompts.join(m.filter(ok).with_columns(cred=(c1+c2)/2).select(["sample_id","cred"]), on="sample_id")
    models[os.path.basename(f)] = (d, score(d.filter(pl.col("domain") != "moral_claims"), bootstrap=1)[0])
def run(seed, out):
    sp.SEED = seed; import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()): sp.main(root, out)
    ids = pl.read_csv(out / "selected_prompts.csv")["sample_id"].implode()
    sub = np.array([score(d.filter(pl.col("sample_id").is_in(ids)), bootstrap=1)[0] for d, _ in models.values()])
    full = np.array([f for _, f in models.values()])
    return np.mean(sub - full), np.mean(np.abs(sub - full)), np.max(np.abs(sub - full)), spearmanr(sub, full)[0]
ours = run(20261114, Path("/tmp/seed_ours"))
others = np.array([run(s, Path(f"/tmp/seed_{s}")) for s in range(100)])
names = ["mean gap", "mean |gap|", "max |gap|", "spearman"]
for i, n in enumerate(names):
    pct = (others[:, i] <= ours[i]).mean()
    print(f"{n:10s} ours {ours[i]:+.2f} | 100 other seeds: median {np.median(others[:, i]):+.2f}, 5-95% [{np.quantile(others[:, i], .05):+.2f}, {np.quantile(others[:, i], .95):+.2f}] | ours at {pct:.0%} percentile")
