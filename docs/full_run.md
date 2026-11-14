# Full run (API models)

Design: the 42-proposition set (`data/full_run/full_run_prompts.jsonl`, 504 prompts) and the 80 known items,
neutral and hedge-hack, judged by the current substitute judges. Budget: $285 total (decided 2026-11-14).
Only Andrei runs it (endpoint credentials). Order: **Grok 4.6 first, check spend, then Kimi K3.**

```bash
uv run --project external/pander-score python -I scripts/run_api_full.py --models grok-4.6
uv run --project external/pander-score python -I scripts/run_api_full.py --models kimi-k3
```

For each model and policy there are two evals: the Pander prompts with judges, and the known items without judges.
Logs go to `logs/full/`. After every eval the script prints target and judge dollars and a running total, and
appends them to `outputs/full/spend.jsonl`.

- **Resuming:** if a run stops, rerun the same command. Target and judge calls come from Inspect's cache, so
  finished work costs nothing again. A cached rerun of 2 prompts took 2 seconds and $0.
- **Errors:** samples that error are retried up to 3 times. More than 5% failed samples stops the eval.
- `--no-cache` forces fresh target calls; use it only for a deliberate rerun.

## Smoke test, 2026-11-14

2 prompts per part, both models, both policies: 8 evals, all succeeded with 0 errors. FINAL parsed everywhere;
known items scored (4/4 correct) and not judged. Cost $0.63.

Per Pander prompt (target + judges), from the smoke test: Kimi about $0.04, Grok about $0.05. Projection for
504 prompts × 2 policies plus known items: **Grok about $52, Kimi about $45**. Grok took about 1.4 minutes per
prompt, end to end; at 16 connections, about 45 minutes per policy if the endpoint allows that concurrency.
