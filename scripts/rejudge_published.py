"""Re-judge the published Pander replies on our subset with the substitute (endpoint) credence judges,
to give pilot references scored by the same judges as our own runs.

    uv run --project external/pander-score python -I scripts/rejudge_published.py <hf v1/benchmark dir> [out dir] [model ...]

Writes <out>/per_model/<same file name>.parquet with the published columns, judge fields replaced, and
symlinks prompt_attributes.parquet, so `check_subset_scores.py <out>` scores it (only its last column,
"our 720 prompts", is meaningful there). Default out: outputs/rejudged. Default models: kimi-k3, grok-4.6.
Judge calls use Pander's judge prompt, parser, parse retry and per-judge GenerateConfig, and Inspect's
cache, so a rerun only pays for what failed. Prints judge token totals per model.
"""
import asyncio, sys
from pathlib import Path

import polars as pl
from pander_score.core.credence_judge import format_judge_prompt, parse_judgment
from pander_score.core.scorers import _JUDGE_CALL_CONFIG
from pander_score.core.util import format_interaction_log

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gateway_judges  # noqa: E402
from api_models import ROOT, resolve_judge  # noqa: E402

FILES = {"kimi-k3": "openai-api-fireworks-accounts-fireworks-models-kimi-k3.parquet",
         "grok-4.6": "grok-grok-4.6.parquet"}
PARSE_RETRIES = 1  # as Pander's _JUDGE_PARSE_MAX_RETRIES


async def judge(model, prompt: str, usage: dict) -> tuple:
    for attempt in range(PARSE_RETRIES + 1):
        config = _JUDGE_CALL_CONFIG if attempt == 0 else _JUDGE_CALL_CONFIG.model_copy(update={"cache": False})
        out = await model.generate(prompt, config=config)
        if out.usage:
            usage["in"] += out.usage.input_tokens; usage["out"] += out.usage.output_tokens
        try:
            j = parse_judgment(out.completion)
            return j.refusal, j.informative, j.credence, j.explanation, out.completion
        except Exception:
            continue
    return None, None, None, None, out.completion


async def rejudge(name: str, root: Path, out_dir: Path, judges: dict) -> None:
    subset = pl.read_csv(ROOT / "data/subset/selected_prompts.csv")["sample_id"]
    prompts = pl.read_ndjson(ROOT / "data/subset/selected_prompts.jsonl").select(
        pl.col("id").alias("sample_id"), "input", "target")
    df = (pl.read_parquet(root / "per_model" / FILES[name])
          .filter(pl.col("published_condition") & pl.col("sample_id").is_in(subset.implode()))
          .join(prompts, on="sample_id", how="left").sort("sample_id"))
    models = [resolve_judge(jid.removeprefix(gateway_judges.PREFIX), cfg) for jid, cfg in judges.items()]
    usage = [{"in": 0, "out": 0} for _ in models]
    sem = asyncio.Semaphore(16)

    async def row(r: dict) -> list:
        if not r["response_text"]:
            return [(None,) * 5 for _ in models]
        log = format_interaction_log([{"role": "user", "content": r["input"]},
                                      {"role": "assistant", "content": r["response_text"]}])
        prompt = format_judge_prompt(r["template_name"] or "implicit_judge", r["target"], log)
        async with sem:
            return await asyncio.gather(*(judge(m, prompt, u) for m, u in zip(models, usage)))

    results = await asyncio.gather(*(row(r) for r in df.iter_rows(named=True)))
    cols = {}
    for i, jid in enumerate(judges, 1):
        cols[f"judge{i}_llm_id"] = [jid] * df.height
        for k, field in enumerate(("refusal", "informative", "credence", "explanation", "raw_completion")):
            cols[f"judge{i}_{field}"] = [res[i - 1][k] for res in results]
    new = df.drop("input", "target").with_columns(**{k: pl.Series(k, v, strict=False) for k, v in cols.items()})
    (out_dir / "per_model").mkdir(parents=True, exist_ok=True)
    new.write_parquet(out_dir / "per_model" / FILES[name])
    failed = sum(r is None for res in results for r in (x[2] for x in res))
    print(f"{name}: {df.height} replies, {failed} judgments without a credence; tokens "
          + ", ".join(f"{jid.removeprefix(gateway_judges.PREFIX)} in {u['in']:,} out {u['out']:,}"
                      for jid, u in zip(judges, usage)))


async def main() -> None:
    root = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "outputs" / "rejudged"
    names = sys.argv[3:] or list(FILES)
    judges = gateway_judges.install()
    out_dir.mkdir(parents=True, exist_ok=True)
    link = out_dir / "prompt_attributes.parquet"
    if not link.exists():
        link.symlink_to(root / "prompt_attributes.parquet")
    for name in names:
        await rejudge(name, root, out_dir, judges)


if __name__ == "__main__":
    asyncio.run(main())
