"""Pick substitute credence judges: re-judge published replies with endpoint candidates and compare
with Pander's original judges on the same replies.

    uv run --project external/pander-score python -I scripts/judge_calibration.py <hf v1/benchmark dir> [n_per_model]

.env: JUDGE_CANDIDATES = JSON {label: endpoint model name}. Labels starting "openai" are compared with
Pander's judge1 (GPT-5.4-mini), "google" with judge2 (Gemini 3 Flash preview). Only labels are printed.
Replies are a seeded sample (seed 0) of the published kimi-k3 and grok-4.6 outputs on our subset
(data/subset/selected_prompts.jsonl). Each candidate uses the GenerateConfig of the judge it replaces.
"""
import asyncio, json, os, sys
from pathlib import Path

import numpy as np
import polars as pl
from dotenv import load_dotenv
from pander_score.core.credence_judge import format_judge_prompt, judge_and_parse, JudgeParseError
from pander_score.core.scorers import CREDENCE_JUDGES, _JUDGE_CALL_CONFIG
from pander_score.core.util import format_interaction_log

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_models import ROOT, endpoint_model  # noqa: E402

PANDER = {"openai": ("judge1", "openai/gpt-5.4-mini-2026-03-17"),
          "google": ("judge2", "google/gemini-3-flash-preview")}
MODELS = {"kimi-k3": "openai-api-fireworks-accounts-fireworks-models-kimi-k3.parquet",
          "grok-4.6": "grok-grok-4.6.parquet"}


def sample_rows(root: Path, n: int) -> pl.DataFrame:
    subset = pl.read_ndjson(ROOT / "data/subset/selected_prompts.jsonl").select(
        pl.col("id").alias("sample_id"), pl.col("input"), pl.col("target"))
    frames = []
    for name, f in MODELS.items():
        df = pl.read_parquet(root / "per_model" / f).join(subset, on="sample_id")
        df = df.filter(pl.col("response_text").str.len_chars() > 0).sort("sample_id")
        frames.append(df.sample(n, seed=0).with_columns(pl.lit(name).alias("model")))
    return pl.concat(frames, how="diagonal_relaxed")


async def judge_all(label: str, real: str, rows: pl.DataFrame) -> list[dict]:
    family = label.split("-")[0]
    config = CREDENCE_JUDGES[PANDER[family][1]]
    model = endpoint_model(label, {label: real}, config, role="judge")
    sem = asyncio.Semaphore(8)

    async def one(r: dict) -> dict:
        log = format_interaction_log([{"role": "user", "content": r["input"]},
                                      {"role": "assistant", "content": r["response_text"]}])
        prompt = format_judge_prompt("implicit_judge", r["target"], log)
        async with sem:
            try:
                out = await judge_and_parse(model, prompt, _JUDGE_CALL_CONFIG)
                j = out.judgment
                return {"ok": True, "informative": j.informative, "credence": j.credence}
            except JudgeParseError:
                return {"ok": False, "informative": None, "credence": None}

    return await asyncio.gather(*(one(r) for r in rows.iter_rows(named=True)))


def compare(label: str, res: list[dict], rows: pl.DataFrame) -> str:
    prefix = PANDER[label.split("-")[0]][0]
    ref_inf = rows[f"{prefix}_informative"].to_list(); ref_c = rows[f"{prefix}_credence"].to_list()
    ok = [r["ok"] for r in res]
    inf_agree = np.mean([r["informative"] == bool(i) for r, i in zip(res, ref_inf) if r["ok"] and i is not None])
    pairs = [(r["credence"], c) for r, i, c in zip(res, ref_inf, ref_c)
             if r["ok"] and r["informative"] and i and r["credence"] is not None and c is not None]
    a, b = np.array(pairs).T if pairs else (np.array([]), np.array([]))
    mae = np.mean(np.abs(a - b)) if len(a) else float("nan")
    within = np.mean(np.abs(a - b) <= 0.2) if len(a) else float("nan")
    r = np.corrcoef(a, b)[0, 1] if len(a) > 2 else float("nan")
    return (f"{label:14s} parsed {np.mean(ok):5.0%}  informative-agree {inf_agree:5.0%}  "
            f"n={len(a):3d}  MAE {mae:.3f}  within0.2 {within:5.0%}  r {r:+.2f}")


async def main() -> None:
    root = Path(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    load_dotenv(ROOT / ".env")
    cands = json.loads(os.environ["JUDGE_CANDIDATES"])
    rows = sample_rows(root, n)
    # Pander's own two judges on the same rows: the agreement ceiling a substitute can aim for
    both = rows.filter(pl.col("judge1_informative") & pl.col("judge2_informative"))
    d = (both["judge1_credence"] - both["judge2_credence"]).abs()
    print(f"{len(rows)} replies. Pander judge1 vs judge2: n={both.height} MAE {d.mean():.3f} "
          f"within0.2 {(d <= 0.2).mean():.0%} r {np.corrcoef(both['judge1_credence'], both['judge2_credence'])[0, 1]:+.2f}")
    results = await asyncio.gather(*(judge_all(l, real, rows) for l, real in cands.items()))
    for label, res in zip(cands, results):
        print(compare(label, res, rows))


asyncio.run(main())
