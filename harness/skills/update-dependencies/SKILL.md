---
name: update-dependencies
description: "Handles the single weekly Dependabot PR: reads the changelogs, fixes breakages on the same branch, keeps ci-gate green and leaves the merge to the owner. Use when the weekly dependency PR is open, labelled needs-fix, or the guard reports it red, even if only one ecosystem broke. Not for urgent single-dependency security fixes (normal task-branch PR) or for merging the PR (owner only)."
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# update-dependencies

Catalog skeleton from engineering-standards (ecosystem 15.5). Repositories copy it to
`.agents/skills/update-dependencies/`, link `.claude/skills/update-dependencies` to it, and tune the commands to their stack.

## Checklist

- [ ] Inputs read (AGENTS.md, the item or diff in scope)
- [ ] Procedure followed with the repository's own commands
- [ ] Evidence collected for every claim
- [ ] Output delivered in the template below

## Procedure

1. Read the PR body (versions per ecosystem) and the tracking issue section written by deps-weekly-guard.
2. For each major bump read the upstream changelog; list breaking changes that touch this repo.
3. Fix breakages on the Dependabot branch in small commits (this stops Dependabot rebases; the guard handles superseding).
4. Run the full check; keep `ci-gate` green; never merge, the owner merges the weekly PR.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Comment-free summary for the owner in the PR description: bumps, breaking changes handled, evidence.
