# API target models

Task: "pick two API models with high published Pander scores (not OpenAI or Google); check access". Checked 2026-11-14.

## Models

| Alias | Published conv. score | Published condition |
|---|---|---|
| `kimi-k3` (Kimi K3) | +7.0 (720-prompt subset: +4.1 [−1.3, +9.0]) | reasoning high |
| `grok-4.6` (Grok 4.6) | +13.8 (720-prompt subset: +11.7 [+5.8, +18.0]) | reasoning high |

- The task asks for high published scores, so the hedge prompt has room to raise the judged score. Anthropic models were
  considered and dropped: every published one is near the floor (Sonnet 4.6 −3.9, Opus 4.6 −3.5, Fable 5 +1.1).
- Kimi K3 is open-weight but too large to run locally, so it counts as an API model.
- Local open-weight models (run by Kacper via Ollama; setup is his task): **Qwen 3.8 27B** at Q3 quantisation and
  **Mistral Small 3.1 24B**. Neither has a published Pander score, so the pilot can't check them against a reference.
  Their families (Alibaba, Mistral) differ from the judges' and from the API targets'.
- Neither family (Moonshot, xAI) is a judge family (judges: GPT-5.4-mini, Gemini 3 Flash).
- Subset numbers are from Stanisław's re-score of the published outputs on our 720 prompts
  (`data/subset/README.md`, `scripts/check_subset_scores.py`). Use them, not the leaderboard scores, as pilot references.
  Both gaps from the full score are within what sampling 60 propositions produces (README: median absolute gap 2.2,
  5–95% of largest gap 3.3–8.6). Kimi's subset interval crosses zero, so a pilot on 5 propositions can't check it tightly.
- Version strings: the endpoint names carry no date. Record the alias and run date; Andrei keeps the alias → endpoint
  name mapping privately.

## Setup

- Only Andrei runs the API models. Endpoint, credentials and the alias → endpoint model name map live only in his
  `.env` (names in `.env.example`). **Confidential: they never go into the repo, docs, logs or shared output.**
- `scripts/api_models.py`: `resolve_model(alias)` returns an Inspect `Model`; `generate_config(alias)` gives Pander's
  published condition for the matching published model (max_tokens 16k, reasoning effort, temperature).
- Inspect only sees `openai-api/target/<alias>` and a placeholder URL. A custom HTTP transport sends each request to the
  real endpoint and hands back a cleaned response: the model name set back to the alias, identifying response headers
  dropped, and error bodies replaced by a generic message with the HTTP status. Checked 2026-11-14 on one real eval per
  model plus a forced error: no endpoint detail in the eval logs, console output or traceback.
- Smoke test (under 1 cent): `uv run --project external/pander-score python -I scripts/api_smoke.py`.

## Cost check (3 conversational prompts per model, published condition)

| Model | Output tokens per reply (incl. reasoning) | Price in/out per M (to confirm) | Per reply |
|---|---|---|---|
| Kimi K3 | 680–760 (220–270 reasoning) | $3 / $15 | ~$0.011 |
| Grok 4.6 | 870–1,530 (390–1,330 reasoning) | $2 / $6 | ~$0.008 |

For 1,600 replies plus 1,600 shorter forced-choice calls: **Kimi about $25, Grok about $17**, before judges. Kimi is close to
the plan's $25-per-model line, so check it in the pilot. There is no per-provider spending cap on this endpoint; track spend
from Inspect usage against the $150 budget.
