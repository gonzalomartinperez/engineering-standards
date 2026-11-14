---
name: score-repo
description: "Runs the repository scorecard, compares it with the committed ratchet baselines and assembles the three-lens evidence pack. Use when preparing a milestone safe point or a release, or when asked for the score or quality status of the repo, even if CI is green. Not for fixing the findings."
allowed-tools: Read, Grep, Glob, Bash
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# score-repo

Catalog skeleton from engineering-standards (ecosystem 15.5). Repositories copy it to
`.agents/skills/score-repo/`, link `.claude/skills/score-repo` to it, and tune the commands to their stack.

## Checklist

- [ ] Inputs read (AGENTS.md, the item or diff in scope)
- [ ] Procedure followed with the repository's own commands
- [ ] Evidence collected for every claim
- [ ] Output delivered in the template below

## Procedure

1. Run the scorecard command from AGENTS.md (M2 delivers it; until then collect CI evidence by hand).
2. Compare each axis with the baseline files; any loosening is a finding.
3. Collect evidence links per rubric criterion; a criterion without evidence is unmet.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Score per axis, regressions against baselines, evidence links.
