# Activation evals (skeleton)

Protocol (ecosystem 15.1): every skill has `evals/triggers.json` (positive and near-miss negative
queries with a fixed 60/40 train/validation split) and `evals/evals.json` (output evals with
assertions, run with and without the skill).

1. A runner executes each trigger query three times on a clean context and records whether the
   skill activated, writing `{"skill": ..., "results": [{query, should_trigger, split, runs}]}`.
2. `python3 tools/activation_evals.py score results.json` reports precision and recall on the
   validation split (a query triggers when at least half of its runs did).
3. `python3 tools/activation_evals.py compare baseline.json candidate.json` fails when validation
   accuracy drops by more than 10 points; a skill change is not merged then.

The runner is part of the M2 eval tooling (it needs a model session; no paid API calls in CI).
Until then, `tools/check_skills.py` validates the structure of every skill and its eval files.
