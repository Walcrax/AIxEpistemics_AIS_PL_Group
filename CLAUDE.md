# AI x Epistemics sprint (Apart, 13–15 Nov 2026): Hedge-Hack

Plan, hypotheses and task board: `sprint_doc.md` (source of truth). Submission due Sun 15 Nov 23:59 AoE.

- Question: can a hedging system prompt raise an LLM-judge honesty score (Pander Score) without changing
  committed answers, and does scoring a forced-choice `FINAL: <option>` answer close the gap?
- Benchmark: Pander Score v1, cloned (gitignored) at `external/pander-score`, pinned commit and notes in
  `docs/pander_setup.md`. Code is MIT, data is CC BY 4.0. Treat it as read-only upstream: wrap it, don't edit it.
- Pipeline: inspect_ai. Pander's credence judges are fixed (GPT-5.4-mini + Gemini 3 Flash) and need OpenAI and
  Google keys. Target models must come from other families.
- Budget $285 total (raised from $150 on 2026-11-14 to keep the current judges with the full design at 42
  propositions). Never launch a full 11,172-prompt Pander run; always stage a subset JSONL.
- Secrets live in `.env` (gitignored). Never commit them.
- Fresh repo started 2026-11-14 for the Hedge-Hack pivot. The old pre-pivot sycophancy pipeline history (incl.
  unpushed `api-smoke-and-items` commits) is backed up at `~/Desktop/AI-x-Epistemics-old-git-backup.git`
  and on GitHub `Walcrax/AI-x-Epistemics-Research-Sprint---AIS-PL-group`.
- Scripts that read untrusted/third-party data: run with `python3 -I`, pass paths as args.
