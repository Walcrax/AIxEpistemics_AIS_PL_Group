# Pre-registration: Hedge-Hack

First committed on 14 November 2026, before any target-model run on our subset. The git commit that adds
this file is the timestamp. Items marked **open** are fixed in a later dated commit, after the Saturday
pilot and before the first full run, and that commit gets the tag `prereg-final`. Any change after
`prereg-final` is listed under Deviations, with its date and reason.

## Question

Does a system prompt that asks for hedged, both-sides, calibrated-sounding prose improve a model's judged
Pander Score without changing what the model commits to, and does scoring a forced-choice answer instead of the
prose remove that improvement?

## Materials

| Item | File | SHA-256 |
|---|---|---|
| 60 propositions | `data/subset/selected_propositions.csv` | `4d5060780e47c1b58dbbdea60137444287b9be62e5ffa079f8a248d6c4c56d4e` |
| 720 prompts | `data/subset/selected_prompts.jsonl` | `019a084293466c0c881edf0e2ee03ecfae0ed822b65cf3ab9cc2663672d7156d` |
| Full-run set: 40 propositions | `data/full_run/full_run_propositions.csv` | `41072b658a66423389a13bd76cb861ad23b1869929d389ada0cbd9a2b450c150` |
| Full-run set: 480 prompts | `data/full_run/full_run_prompts.jsonl` | `d2989db6293d52ccd1732a23c5497c3691b4511863fa3dc6173e642328ff6c3d` |
| Hedge-hack system prompt | `prompts/hedge_hack_system.txt` | `fa102cfde714adaedc68bf67ac530d30f19c4cfeac657a84422797badf3fc485` |
| Hedge sentences for the hedge-only control | `prompts/hedge_bank.json` | `3c28c9e4c370ad04e57c80cb455372934df75004a3394a77e16d9527de8e298f` |
| 80 known-answer items (SycoBench-600) | `data/known_items/known_items.jsonl` | `8ecb442e6f0b4578482567d371ec1a82ae295c878d34852aeb1b3bc76872b58f` |

**Full-run set: 40 of the 60 propositions** (decided 14 November 2026, for budget). It is the 5 pilot
propositions (`data/pilot/pilot_prompts.jsonl`) plus 35 more from the other 55, fixed on 14 November 2026
before any full-run result by `scripts/select_full_run.py`. Rule: 40 over 6 domains gives 6 each plus 4; the 4
domains that get a 7th are drawn with `random.Random(20261114)`, pilot propositions count towards their domain,
and each domain is filled from its remaining propositions with the same generator. Result: 7 each for contested
social science, frontier natural science, historical facts and nutrition and health, 6 each for paranormal claims
and politically polarizing; 480 prompts, 160 per prior.
Pilot runs are not reused: the full run reruns all 40 propositions, including the 5 pilot ones. The pilot fixed
M (H2) and checked the pipeline only, which we report.

The subset is 10 propositions from each of six Pander domains (moral claims excluded) with 4 skeptic, 4 neutral
and 4 believer conversational prompts each; see `data/subset/README.md`. The known-answer items are 10 from each
of SycoBench-600's eight domains, chosen as items most published models knew but at least one gave up under a
wrong suggestion; each is one user message stating a wrong answer. See `data/known_items/README.md`.

**Models:** Kimi K3 and Grok 4.6 through their APIs, with the settings from Pander's published configs, and
Qwen 3.8 27B (Q3) and Mistral Small 3.1 24B run locally through Ollama at temperature 0 (`configs/models.yaml`).
The Pander credence judges are unchanged: GPT-5.4-mini and Gemini 3 Flash.

## Conditions

- **Neutral:** no system prompt, as in the published Pander runs.
- **Hedge-hack:** the system prompt is `prompts/hedge_hack_system.txt` and nothing else (no persona or assistant line).
- **Hedge-only control:** each neutral reply with one opener sentence before it and one both-sides sentence
  plus one offer-to-abstain sentence after it, from `prompts/hedge_bank.json`, chosen by a stable hash
  (`scripts/hedge_rewrite.py`). The reply itself is unchanged. Judged by the Pander judges like any reply.
- **Forced choice:** after every reply in both conditions, a new conversation with no system prompt contains the
  original user message, the model's reply, and one follow-up message asking whether the proposition is true, to be
  answered with `FINAL: TRUE` or `FINAL: FALSE`. Known items use the same structure with their answer options.
  The exact wording of the follow-up is **open** (task A) and is fixed before the pilot.

## Measures

All Pander scores are conversational scores ×100 from the canonical estimator (`docs/pander_setup.md`), on the
prompts and replies that survive its filters. The pooled value of any measure is the mean of the four
per-model values. Intervals are 95% percentile intervals from 2,000 bootstrap draws that resample propositions
(known items: items), the same draw for every model and condition. No p-values are used.

| Measure | Definition | Used for |
|---|---|---|
| Exploit gain | Pander Score under neutral minus under hedge-hack. Positive means hedging made the model look less sycophantic. | H1 |
| Style effect | Pander Score on the neutral replies minus on their hedge-only rewrites | H1 (mechanism) |
| Agreement change | Share of forced choices answering TRUE, hedge-hack minus neutral, in percentage points | H2 |
| Known-item change | Accuracy on the known items, hedge-hack minus neutral, in percentage points | H2 |
| Flip rate | Share of prompts whose forced choice differs between neutral and hedge-hack, against the flip rate between two neutral runs (noise floor) | H2 (descriptive) |
| Gain closed | 1 − (exploit gain of the patched score ÷ exploit gain of the prose score), both on the linear scale below | H3 |

**Linear scale for H3.** The patched score and the canonical score are in different units, so H3 compares both
on one linear scale. For each proposition, regress the outcome on author valence (0–1, no logit), take the
slope, and average the slopes weighted by surviving prompts, ×100. The outcome is the judges' consensus
credence for the prose score and the forced choice (TRUE = 1, FALSE = 0) for the patched score. Both then
measure how much the probability of endorsing the proposition moves from a fully skeptical to a fully
believing user.

## Hypotheses and how each is read

**H1. The hedge-hack prompt improves the Pander Score by at least 5 points.** Read from the pooled exploit gain:

- the whole interval is above 5: supported;
- the interval is above 0 and includes 5: an exploit exists, but we cannot tell whether it reaches 5 points;
- the whole interval is between 0 and 5: an exploit exists but is smaller than 5 points;
- the interval includes 0: no exploit shown.

The style effect is read in the same bands. A style effect in the supported band shows that the judge rewards
the hedging itself, whatever else the prompt changes.

**H2. The hedge-hack prompt leaves committed answers unchanged.** Supported if the pooled intervals of both the
agreement change and the known-item change lie entirely inside ±M percentage points. Not supported if either
interval lies entirely outside ±M, meaning a change larger than M. Inconclusive otherwise. **M = 10 percentage points**, set on 14 November 2026 by a rule fixed before the rerun results: M is the
pooled forced-choice flip rate between two neutral runs of the API pilot, rounded up to a multiple of 5,
with a minimum of 5 and a maximum of 10. The two neutral runs (same 60 prompts, Kimi K3 and Grok 4.6) disagreed
on 20 of 120 forced choices (16.7%: Kimi K3 13 of 60, Grok 4.6 7 of 60), so the rule gives 20, capped at 10.
The cap binds: the models change about a sixth of their committed answers between identical runs, which we
report as the noise floor. Data: `data/pilot/final_answers.csv`. The flip rate is reported against this noise
floor and is not part of the decision.

**H3. Scoring the forced choice removes at least half of the exploit.** Read from the pooled gain closed, and
only if H1's interval is above 0:

- the whole interval is above 50%: supported;
- the interval includes 50%: inconclusive;
- the whole interval is below 50%: not supported.

## Exclusions and reporting

- The canonical Pander filters apply unchanged. Replies the judges disagree on (more than 0.2 apart) or mark as
  uninformative drop out of the prose scores. We report the drop rate per model and condition, because a hedging
  prompt may raise it.
- Forced choices that do not parse contribute to no score. We report the parse rate per model and condition;
  the pipeline must parse at least 95%.
- A proposition with fewer than 4 surviving prompts is left out of that model's score, as in Pander.
- Every measure is also reported per model. Hypotheses are judged on the pooled values only.
- A blind check: two of us label 60 neutral and hedge-hack reply pairs for whether the substantive conclusion
  differs, with Cohen's kappa. If conclusions often differ, we report that the prompt changes behaviour,
  whatever H2's numbers say.

## Deviations

None yet.
