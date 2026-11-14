"""Judge exported local-model replies with the endpoint substitute judges, then tabulate the pilot checks.

    uv run --project external/pander-score python -I scripts/judge_local_replies.py <hf v1/benchmark dir> <export.jsonl> [...]

The local models run on Kacper's machine without judges (the judges need the endpoint credentials, which
stay in Andrei's .env). He exports with run_local_batch.py (or export_pipeline_results.py) and sends the
`pipeline_results.jsonl`; Andrei runs this script on it. Only Pander-subset rows are judged (known items are
scored by FINAL: accuracy, not by the credence judge).

Writes outputs/local_judged/judged.jsonl (input rows plus judge fields) and prints, per model and policy:
Pander score on the rows given, refusal rate (either judge), FINAL: parse rate, mean credence. The local
models have no published Pander score, so there is no reference column. Judge calls use Inspect's cache,
so rerunning on the same replies is free.
"""
import asyncio, json, sys
from pathlib import Path

import polars as pl
from pander_score.core.credence_judge import format_judge_prompt
from pander_score.core.util import format_interaction_log

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gateway_judges  # noqa: E402
from api_models import ROOT, resolve_judge  # noqa: E402
from rejudge_published import judge  # noqa: E402
from run_api_pilot import REFUSAL_MAX, PARSE_MIN, fmt_score, kept_credences  # noqa: E402
from select_propositions import screen  # noqa: E402

OUT = ROOT / "outputs" / "local_judged" / "judged.jsonl"
FIELDS = ("refusal", "informative", "credence", "explanation", "raw_completion")


async def judge_rows(rows: list[dict]) -> list[dict]:
    judges = gateway_judges.install()
    models = [resolve_judge(jid.removeprefix(gateway_judges.PREFIX), cfg) for jid, cfg in judges.items()]
    usage = [{"in": 0, "out": 0} for _ in models]
    sem = asyncio.Semaphore(16)

    async def one(r: dict) -> dict:
        out = dict(r)
        if not r.get("response_text"):
            res = [(None,) * 5 for _ in models]
        else:
            log = format_interaction_log([{"role": "user", "content": r["input"]},
                                          {"role": "assistant", "content": r["response_text"]}])
            prompt = format_judge_prompt("implicit_judge", r["target"], log)
            async with sem:
                res = await asyncio.gather(*(judge(m, prompt, u) for m, u in zip(models, usage)))
        for i, (jid, vals) in enumerate(zip(judges, res), 1):
            out[f"judge{i}_llm_id"] = jid
            out.update({f"judge{i}_{f}": v for f, v in zip(FIELDS, vals)})
        return out

    judged = await asyncio.gather(*(one(r) for r in rows))
    print("judge tokens in/out: " + ", ".join(
        f"{jid.removeprefix(gateway_judges.PREFIX)} {u['in']:,}/{u['out']:,}" for jid, u in zip(judges, usage)))
    return judged


def main() -> None:
    hf_root, exports = Path(sys.argv[1]), [Path(p) for p in sys.argv[2:]]
    if not exports:
        sys.exit(__doc__)
    rows = [json.loads(l) for p in exports for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("dataset_kind", "subset") == "subset"]
    print(f"{len(rows)} Pander-subset replies from {len(exports)} file(s)")
    judged = asyncio.run(judge_rows(rows))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in judged), encoding="utf-8")

    valence = screen(pl.read_parquet(hf_root / "prompt_attributes.parquet")).select("sample_id", "valence")
    df = pl.DataFrame([{k: r.get(k) for k in ("sample_id", "proposition_id", "target_model", "policy",
                        "final_parsed", "judge1_credence", "judge2_credence", "judge1_informative",
                        "judge2_informative", "judge1_refusal", "judge2_refusal")} for r in judged],
                      infer_schema_length=None)
    hdr = f"{'model':24s} {'policy':10s} {'n':>4s} {'score':>24s} {'refusal':>7s} {'FINAL':>6s} {'mean cred':>9s}  checks"
    print(hdr); print("-" * len(hdr))
    for (model, policy), g in sorted(df.group_by(["target_model", "policy"]), key=lambda t: t[0]):
        kept = kept_credences(g, "judge1_credence", "judge2_credence", "judge1_informative",
                              "judge2_informative").join(valence, on="sample_id")
        refusal = float((g["judge1_refusal"].fill_null(False) | g["judge2_refusal"].fill_null(False)).mean())
        parse = float(g["final_parsed"].is_not_null().mean())
        checks = [f"FINAL>=95% {'ok' if parse >= PARSE_MIN else 'FAIL'}"]
        if policy == "hedge_hack":
            checks.append(f"refusal<5% {'ok' if refusal < REFUSAL_MAX else 'FAIL'}")
        print(f"{model:24s} {policy:10s} {g.height:4d} {fmt_score(kept):>24s} {refusal:7.1%} {parse:6.1%} "
              f"{kept['cred'].mean() if kept.height else float('nan'):9.3f}  {', '.join(checks)}")
    print(f"-> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
