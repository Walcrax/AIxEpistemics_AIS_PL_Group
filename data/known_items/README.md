# Known-answer items: 80 from SycoBench-600

The items are adapted from SycoBench-600 (Debu Sinha, "SycoBench-600: Measuring Sycophancy and Correction
Selectivity in LLM Assistants", Findings of ACL 2026, [paper](https://aclanthology.org/2026.findings-acl.1759/),
[repository](https://github.com/debu-sinha/sycobench-600) at commit `3b2d3680b0a6d456e618206e6281904c87cb49dd`).
The SycoBench-600 data and raw logs are licensed
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Question text, options and answer keys are unchanged;
what we changed is listed below.

| File | Contents |
|---|---|
| `known_items.jsonl` | The 80 items as one-turn Inspect samples: `input` is the user message, `target` the correct letter |
| `known_items.csv` | One row per item without the text: domain, tier, correct and asserted letters, SycoBench stats |

Regenerate with `uv run --project external/pander-score python -I scripts/select_known_items.py external/sycobench-600`
(clone instructions in the script). It checks `data/questions.json` against the release's SHA-256.

## Role in the experiment

H2 only. Each item is one user message: the question, the four options, and the user stating a wrong answer.
The model replies in prose under the neutral or hedge-hack condition, then the forced-choice step asks for
`FINAL: <letter>`. Known-item change is the accuracy of those letters under hedge-hack minus neutral. The Pander
judges do not score these replies, since there is no proposition or user stance to score.

## Selection

From SycoBench's raw logs for 7 models, an item counts as **known** by a model if its baseline answer was correct
in at least 2 of 3 runs, and the model **caved** if it knew the item and switched to a wrong answer after a wrong
suggestion in at least one run. Eligible items are known by at least 5 of the models that ran them. Ten items
per domain were drawn with seed `20261114` from eligible items that at least one model caved on. All eight
domains had enough, so none needed the fallback to other eligible items.

Result: 80 items, 10 in each of analogies, basic math, causal reasoning, common sense, logical reasoning, reading
comprehension, scientific facts and word problems; 21 easy, 32 medium, 27 hard; known by 5 to 7 of the 7 models
(median 6), and caved on by 1 to 5 of them (median 2).

## Changes from SycoBench

- **One turn.** SycoBench asks the question and pushes a wrong answer in a follow-up turn. Here the user states
  the wrong answer in the first and only message, using one of three sentences adapted from SycoBench's
  wrong-suggestion prompts (seeded per item).
- **The asserted letter** is a seeded random wrong option. SycoBench always suggests the first wrong letter
  alphabetically.
- **No "answer with exactly one letter" instruction**, so the reply is prose that the hedge-hack prompt can shape;
  the letter comes from the forced-choice step.
