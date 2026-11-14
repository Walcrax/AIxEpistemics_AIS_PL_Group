# Full-run set

40 of the 60 subset propositions, with all 12 prompts each (480 prompts, 160 per prior). It is the 5 pilot
propositions plus 35 more, balanced across domains, from `scripts/select_full_run.py` (seed 20261114; the rule is
in the script and the pre-registration).

| Domain | Propositions | Of which pilot |
|---|---|---|
| contested social science | 7 | 0 |
| frontier natural science | 7 | 1 |
| historical facts | 7 | 1 |
| nutrition and health | 7 | 1 |
| paranormal claims | 6 | 1 |
| politically polarizing | 6 | 1 |

- `full_run_propositions.csv`: the 40 propositions (subset columns plus `in_pilot`).
- `full_run_prompts.jsonl`: the 480 prompts, unchanged subset rows, ready for `--subset-path` (local runner) or
  `hedge_hack_eval(subset_path=...)`.

The full run reruns all 40 propositions; pilot runs are not reused. Source: Pander Score v1 (CC BY 4.0), see
`data/subset/README.md`.
