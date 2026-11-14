# Pander Score subset: 60 propositions × 12 prompts

The files in this folder are adapted from the Pander Score v1 dataset
([sophronresearch/pander-score](https://huggingface.co/datasets/sophronresearch/pander-score), revision
`233e697f341d63d52d406dd0c5f8b838c4bee671`), CC BY 4.0, by Botas, de Font-Reaulx and Hewitt,
[arXiv 2606.07897](https://arxiv.org/abs/2606.07897). We selected a subset and added metadata fields
(`domain`, `author_valence`, `rank_in_prior`, `in_4_2_4`). Prompt text, `id`, `target` and the original
metadata are unchanged.

| File | Contents |
|---|---|
| `selected_propositions.csv` | The 60 propositions: id, domain, area, text |
| `selected_prompts.jsonl` | The 720 prompts as Inspect samples, ready for `json_dataset` |
| `selected_prompts.csv` | The same prompts as a flat index, without the text |

Regenerate with `uv run --project external/pander-score python -I scripts/select_propositions.py <hf v1/benchmark dir>`.
The script checks the input files against the release manifest's SHA-256 hashes.

## Selection rule

- Only conversational prompts that pass the released prompt screens: author-valence judges within 0.2,
  no substantive new evidence, Truth Matters true at certainty ≥ 0.90 from both judges.
- Eligible propositions have at least 4 screened prompts at each prior: 119 of 349.
  The original 5 skeptic / 2 neutral / 5 believer plan left only 48 eligible, none in moral claims.
- Moral claims is excluded: the Truth Matters screen removes most of it, and only 3 of its propositions are eligible.
- Ten propositions per remaining domain, spread across areas, seed `20261114`. Each proposition gets
  4 skeptic, 4 neutral and 4 believer prompts, alternating between the two elicitor models.
  Rows with `in_4_2_4 = true` give a 600-prompt variant (two neutral prompts per proposition dropped) if we need to cut cost.

Why 4/4/4 rather than 4/2/4 or a looser mix: neutral prompts add little to the slope (4/2/4 has about 2% more
slope error per proposition), but they leave room for dropped replies, which may rise under the hedge-hack prompt.
A fixed split gives every proposition the same leverage on the slope; a 3/6/3 proposition has about 11% more slope error.

## Check on the published outputs

`scripts/check_subset_scores.py` reimplements the conversational estimator and reproduces all 18 published
conversational scores. Conversational Pander Score × 100 with 95% bootstrap intervals; n is the number of
propositions scored:

| Model | Full, 7 domains | Full, 6 domains | Our 720 prompts |
|---|---|---|---|
| claude-fable-5 | +1.1 [−1.3, +3.6] | −0.5 [−3.1, +1.9] | −4.1 [−12.3, +3.0], n=56 |
| claude-opus-4-6 | −3.5 [−5.5, −1.5] | −4.0 [−6.0, −1.8] | −6.0 [−11.0, −0.9] |
| claude-sonnet-4-6 | −3.9 [−6.0, −2.0] | −4.1 [−6.3, −2.1] | −3.7 [−9.1, +1.6] |
| gemini-3-flash-preview | +26.0 [+23.1, +29.2] | +25.8 [+22.7, +29.1] | +28.2 [+20.7, +35.9] |
| gemini-3.1-pro-preview | +22.7 [+19.3, +26.2] | +21.8 [+18.4, +25.1] | +27.8 [+17.7, +39.5] |
| gemini-3.5-flash | +23.3 [+20.5, +26.3] | +21.9 [+18.8, +25.2] | +24.3 [+17.0, +32.0] |
| gemini-3.7-flash | +15.7 [+12.9, +18.6] | +13.6 [+10.6, +16.7] | +15.6 [+8.1, +23.6] |
| grok-4-1-fast-reasoning | +34.8 [+31.1, +38.6] | +32.6 [+28.9, +36.5] | +37.6 [+29.6, +47.0] |
| grok-4.20-0309-reasoning | +19.3 [+16.3, +22.2] | +17.9 [+15.2, +20.7] | +13.2 [+6.8, +19.4] |
| grok-4.6 | +13.8 [+11.2, +16.8] | +11.7 [+9.1, +14.5] | +11.7 [+5.8, +18.0] |
| inkling | +18.4 [+15.9, +21.0] | +17.4 [+14.6, +20.3] | +22.6 [+16.7, +29.5] |
| kimi-k3 | +7.0 [+5.1, +9.0] | +5.8 [+3.9, +7.9] | +4.1 [−1.3, +9.0] |
| muse-spark-1.1 | +4.6 [+1.7, +7.6] | +3.2 [+0.3, +6.1] | +5.4 [−1.9, +13.0] |
| glm-5.2 | +28.2 [+25.3, +31.2] | +27.5 [+24.4, +30.7] | +26.5 [+19.1, +33.9] |
| gpt-5.4 | +14.3 [+12.3, +16.4] | +13.2 [+11.2, +15.3] | +15.4 [+10.2, +21.1] |
| gpt-5.4-mini | +16.4 [+14.4, +18.6] | +15.5 [+13.5, +17.7] | +16.6 [+10.3, +23.1] |
| gpt-5.6-sol | +6.6 [+4.9, +8.2] | +5.1 [+3.4, +6.8] | +7.5 [+3.8, +11.7] |
| gpt-5.6-terra | +9.7 [+7.8, +11.8] | +8.4 [+6.4, +10.4] | +10.2 [+5.7, +14.8] |

All 60 propositions keep at least 4 prompts after the credence-judge filter for every model except
claude-fable-5 (56 of 60).

Against the full 6-domain scores, our draw has a mean gap of +1.1 points, a mean absolute gap of 2.6, a largest gap
of 6.0 (gemini-3.1-pro) and a Spearman rank correlation of 0.96 across the 18 models. In 100 other seeds of the
same procedure (`scripts/seed_baseline.py`) the median values are +1.5, 2.2, 5.8 and 0.98, and the 5–95% ranges are
[−1.2, +3.2], [1.4, 3.3], [3.3, 8.6] and [0.96, 0.99]. Our draw is typical, so we keep the seed chosen before this check.
Gaps of this size are expected from sampling 60 propositions, so the pilot should compare a model with the
"Our 720 prompts" column, not with its leaderboard score. Subset scores are not leaderboard-comparable.
