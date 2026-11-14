# Full-run set

42 of the 60 subset propositions, 7 per domain, with all 12 prompts each (504 prompts, 168 per prior). It is the 5
pilot propositions plus 37 more, from `scripts/select_full_run.py` (seed 20261114; the rule is in the script and
the pre-registration).

| Domain | Propositions | Of which pilot |
|---|---|---|
| contested social science | 7 | 0 |
| frontier natural science | 7 | 1 |
| historical facts | 7 | 1 |
| nutrition and health | 7 | 1 |
| paranormal claims | 7 | 1 |
| politically polarizing | 7 | 1 |

- `full_run_propositions.csv`: the 42 propositions (subset columns plus `in_pilot`).
- `full_run_prompts.jsonl`: the 504 prompts, unchanged subset rows, ready for `--subset-path` (local runner) or
  `hedge_hack_eval(subset_path=...)`.

The full run reruns all 42 propositions; pilot runs are not reused. Source: Pander Score v1 (CC BY 4.0), see
`data/subset/README.md`.
