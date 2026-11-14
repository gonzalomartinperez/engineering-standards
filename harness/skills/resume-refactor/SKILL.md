---
name: resume-refactor
description: "Resumes the master refactor from git alone: reads RESUME.md, the ecosystem tracker and progress.md, checks out the last checkpoint and continues with the first unchecked item. Use when a new session starts on these repositories or when asked \"where were we\" or \"continue the refactor\", even if you remember earlier work. Not for starting new milestones the owner has not opened."
allowed-tools: Read, Grep, Glob, Bash
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# resume-refactor

Catalog skeleton from engineering-standards (ecosystem 15.5). Repositories copy it to
`.agents/skills/resume-refactor/`, link `.claude/skills/resume-refactor` to it, and tune the commands to their stack.

## Checklist

- [ ] Inputs read (AGENTS.md, the item or diff in scope)
- [ ] Procedure followed with the repository's own commands
- [ ] Evidence collected for every claim
- [ ] Output delivered in the template below

## Procedure

1. Read `docs/master-plan/RESUME.md`, then `engineering-standards/progress/ecosystem.md`, then this repo's `progress.md`.
2. `git fetch --tags`; confirm `develop` is at or after the last `checkpoint/M<n>` tag and is green.
3. Pick the first unchecked item of the current milestone and hand it to implement-task.
4. Never resume from memory or chat history; if git and the tracker disagree, trust git and record the discrepancy.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Current milestone, last checkpoint SHA, next item, blockers.
