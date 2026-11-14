"""Seeded, domain-balanced selection of Pander Score propositions and prompts.

    uv run --project external/pander-score python -I scripts/select_propositions.py <hf v1/benchmark dir> [out_dir]

Input is the Hugging Face dataset sophronresearch/pander-score at revision
233e697f341d63d52d406dd0c5f8b838c4bee671 (see docs/pander_setup.md); file hashes are checked.
Output (default data/subset/): selected_propositions.csv, selected_prompts.csv, selected_prompts.jsonl.

Prompt screens are the released Pander Score ones (core/metrics.py, with_pander_score_exclusions):
  * conversational prompts only (is_artifact == False)
  * author-valence consensus: both judges present and within 0.2
  * new evidence: defensive OR, so a prompt is dropped if either judge flags substantive new evidence
  * Truth Matters: both judges true with certainty >= 0.90
A proposition is eligible if it has at least 4 screened prompts at each prior (skeptic, neutral,
believer): 119 of 349. Moral claims are excluded, because Truth Matters removes most of that domain
and only 3 of its propositions are eligible. Ten propositions are drawn per remaining domain, spread
across areas (round-robin over areas in a seeded random order). Within each proposition, 4 prompts
are drawn per prior, alternating between the two elicitor models. Neutral prompts are ranked, so
`in_4_2_4` (neutral rank <= 2) gives the 10-prompt variant without reselection.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

SEED = 20261114
PER_DOMAIN = 10
PER_PRIOR = 4
PRIORS = ("skeptic", "neutral", "believer")
EXCLUDED_DOMAINS = {"moral_claims"}
NE = "DOES_INTRODUCE_SUBSTANTIVE_NEW_EVIDENCE"
SHA256 = {  # from v1/metadata/release_manifest.json at the pinned revision
    "prompt_attributes.parquet": "06b60740cc75d76d910d602b24df757ddcf3aaea89487700bcc709c8c253e8a0",
    "prompts.jsonl": "c6675c63bcadff17bc7f817c95926af917c363a6dc7bd868fc930800af53c4cb",
    "propositions.csv": "cc5fff45e7c9ad710b4e88ba8acc43734d93c826e8c3eb5e420c3b6ae12d5e9d",
}


def check_inputs(root: Path) -> None:
    for name, want in SHA256.items():
        got = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if got != want:
            raise SystemExit(f"{name}: sha256 {got} does not match the pinned revision")


def screen(attrs: pl.DataFrame) -> pl.DataFrame:
    v1, v2 = pl.col("prompt_judge1_author_valence"), pl.col("prompt_judge2_author_valence")
    l1, l2 = pl.col("evidence_cat_judge1_label"), pl.col("evidence_cat_judge2_label")
    tm = pl.lit(True)
    for j in ("tm_judge1", "tm_judge2"):
        tm = tm & (pl.col(f"{j}_truth_matters") == True) & (pl.col(f"{j}_certainty") >= 0.90 - 1e-9)  # noqa: E712
    keep = (
        ~pl.col("is_artifact")
        & v1.is_not_null() & v2.is_not_null() & ((v1 - v2).abs() <= 0.2 + 1e-9)
        & ~((l1 == NE).fill_null(False) | (l2 == NE).fill_null(False)) & ~(l1.is_null() & l2.is_null())
        & tm.fill_null(False)
    )
    return attrs.filter(keep).with_columns(valence=(v1 + v2) / 2)


def pick_prompts(g: pl.DataFrame, rng: np.random.Generator) -> pl.DataFrame:
    out = []
    for prior in PRIORS:
        pool = g.filter(pl.col("prior") == prior).sort("sample_id")
        by_gen = {}
        for gen in sorted(pool["generator_llm_id"].unique().to_list()):
            ids = pool.filter(pl.col("generator_llm_id") == gen)["sample_id"].to_list()
            by_gen[gen] = list(rng.permutation(ids))
        order = []
        while any(by_gen.values()):  # alternate elicitors so any prefix is as balanced as possible
            for gen in sorted(by_gen):
                if by_gen[gen]:
                    order.append(by_gen[gen].pop())
        chosen = order[:PER_PRIOR]
        out.append(pl.DataFrame({"sample_id": chosen, "rank_in_prior": list(range(1, len(chosen) + 1))}))
    return pl.concat(out)


def main(root: Path, out_dir: Path) -> None:
    check_inputs(root)
    rng = np.random.default_rng(SEED)
    attrs = pl.read_parquet(root / "prompt_attributes.parquet")
    screened = screen(attrs)
    counts = screened.group_by(["proposition_id", "prior"]).len().pivot(on="prior", index="proposition_id", values="len").fill_null(0)
    eligible = counts.filter(pl.all_horizontal(pl.col(p) >= PER_PRIOR for p in PRIORS))["proposition_id"]
    props = (
        pl.read_csv(root / "propositions.csv")
        .rename({"id": "proposition_id"})
        .filter(pl.col("proposition_id").is_in(eligible.implode()) & ~pl.col("domain").is_in(list(EXCLUDED_DOMAINS)))
    )

    selected = []
    for domain in sorted(props["domain"].unique().to_list()):
        d = props.filter(pl.col("domain") == domain).sort("proposition_id")
        areas = {
            area: list(rng.permutation(d.filter(pl.col("area") == area)["proposition_id"].to_list()))
            for area in sorted(d["area"].unique().to_list())
        }
        area_order = list(rng.permutation(sorted(areas)))
        picked = []
        while len(picked) < PER_DOMAIN and any(areas.values()):
            for area in area_order:
                if areas[area] and len(picked) < PER_DOMAIN:
                    picked.append(areas[area].pop())
        if len(picked) < PER_DOMAIN:
            raise SystemExit(f"{domain}: only {len(picked)} eligible propositions")
        selected += picked

    sel_props = props.filter(pl.col("proposition_id").is_in(selected)).sort(["domain", "area", "proposition_id"])
    picks = pl.concat(
        pick_prompts(screened.filter(pl.col("proposition_id") == pid), rng)
        for pid in sel_props["proposition_id"].to_list()
    )
    prompts = (
        picks.join(screened, on="sample_id")
        .with_columns(in_4_2_4=(pl.col("prior") != "neutral") | (pl.col("rank_in_prior") <= 2))
        .sort(["domain", "proposition_id", "prior", "rank_in_prior"])
    )

    texts = {}
    with open(root / "prompts.jsonl") as f:
        for line in f:
            r = json.loads(line)
            texts[r["id"]] = r
    missing = set(prompts["sample_id"].to_list()) - set(texts)
    if missing:
        raise SystemExit(f"{len(missing)} selected prompts missing from prompts.jsonl")

    out_dir.mkdir(parents=True, exist_ok=True)
    sel_props.write_csv(out_dir / "selected_propositions.csv")
    prompts.select(["sample_id", "proposition_id", "domain", "prior", "rank_in_prior", "in_4_2_4", "valence",
                    "generator_llm_id", "length", "tone", "user_role"]).write_csv(out_dir / "selected_prompts.csv")
    with open(out_dir / "selected_prompts.jsonl", "w") as f:
        for r in prompts.iter_rows(named=True):
            sample = dict(texts[r["sample_id"]])  # unchanged Pander sample: id, input, target, metadata
            sample["metadata"] = {**sample["metadata"], "domain": r["domain"], "author_valence": r["valence"],
                                  "rank_in_prior": r["rank_in_prior"], "in_4_2_4": r["in_4_2_4"]}
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"seed={SEED}: {len(eligible)} eligible propositions; selected {sel_props.height} propositions, {prompts.height} prompts")
    print(sel_props.group_by("domain").agg(n=pl.len(), areas=pl.col("area").n_unique()).sort("domain"))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "subset")
