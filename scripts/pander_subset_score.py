"""Score published Pander outputs on a seeded subset: per proposition, sample a prior mix of
screened conversational prompts (default 5 skeptic / 2 neutral / 5 believer; falls back to any
prior to fill 12 if --relaxed). Validates the subset scoring path with zero API calls.

uv run --project external/pander-score python scripts/pander_subset_score.py <hf v1/benchmark dir> [--relaxed]
"""
import random, sys
from pathlib import Path
import polars as pl
from pander_score.core.metrics import compute_pander_score, with_pander_score_exclusions
from pander_score.data import load_model_results

root = Path(sys.argv[1]); relaxed = "--relaxed" in sys.argv
attrs = pl.read_parquet(root / "prompt_attributes.parquet")
# prompt-side screens only (response consensus needs model outputs): reuse canonical filter with dummy credences
probe = attrs.with_columns(judge1_credence=pl.lit(0.5), judge2_credence=pl.lit(0.5),
                           judge1_informative=pl.lit(True), judge2_informative=pl.lit(True))
screened = with_pander_score_exclusions(probe).filter(~pl.col("is_artifact"))
need = {"skeptic": 3, "neutral": 2, "believer": 3} if relaxed else {"skeptic": 5, "neutral": 2, "believer": 5}
rng = random.Random(0); chosen = []
for pid, g in sorted(screened.group_by("proposition_id"), key=lambda t: t[0][0]):
    by = {p: sorted(g.filter(pl.col("prior") == p)["sample_id"].to_list()) for p in need}
    if any(len(by[p]) < n for p, n in need.items()): continue
    pick = [s for p, n in need.items() for s in rng.sample(by[p], n)]
    rest = sorted(set(g["sample_id"].to_list()) - set(pick))
    pick += rng.sample(rest, min(12 - len(pick), len(rest)))
    if len(pick) == 12: chosen += pick
ids = set(chosen)
print(f"subset: {len(ids)//12} propositions x 12 prompts ({'relaxed 3/2/3+fill' if relaxed else '5/2/5'})")
print(f"{'model':58s} {'full conv':>18s} {'subset':>22s} props")
for f in sorted((root / "per_model").glob("*.parquet")):
    model = pl.read_parquet(f, columns=["target_model"])["target_model"][0]
    df = load_model_results(root, model).filter(~pl.col("is_artifact"))
    full = compute_pander_score(df); sub = compute_pander_score(df.filter(pl.col("sample_id").is_in(ids)))
    print(f"{model:58s} {100*full.score:+6.1f} [{100*full.ci_low:+.1f},{100*full.ci_high:+.1f}]"
          f"  {100*sub.score:+6.1f} [{100*sub.ci_low:+.1f},{100*sub.ci_high:+.1f}]  {sub.n_props}")
