---
name: implement-task
description: "Takes one ready roadmap item through the per-PR pipeline: worktree, tests first, local checks, PR with evidence, review chain, merge on green ci-gate. Use when the user or the orchestrator says \"implement M1-07\", \"do the next roadmap task\" or \"ship this item\", even if no PR is mentioned. Not for reviewing someone else's change (use review-change) or for the weekly dependency PR (use update-dependencies)."
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# implement-task

Catalog skeleton from engineering-standards (ecosystem 15.5). Repositories copy it to
`.agents/skills/implement-task/`, link `.claude/skills/implement-task` to it, and tune the commands to their stack.

## Checklist

- [ ] Inputs read (AGENTS.md, the item or diff in scope)
- [ ] Procedure followed with the repository's own commands
- [ ] Evidence collected for every claim
- [ ] Output delivered in the template below

## Procedure

1. Read AGENTS.md, `docs/master-plan/roadmap.md` (the item and its acceptance criteria) and `progress.md`.
2. `git fetch` and create a worktree under `../wt/<repo>-<slug>` on `<type>/<milestone>-<slug>` from `origin/develop` (main-only repos: `origin/main`).
3. Write or extend the failing test at the right layer first, then implement; keep one concern and about 400 changed lines.
4. Run the AGENTS.md check command through the test-runner agent; fix until green.
5. Run the review chain: reviewer agent, Codex second opinion (or the documented fallback), architecture-reviewer for structural changes; reproduce every finding before acting.
6. Open the PR with the template (what, why, evidence, risk, rollback); merge only with `gh pr checks <n> --watch && gh pr merge <n> --merge --delete-branch`.
7. Remove the worktree and tick the item in `progress.md`.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

PR URL, CI run URL, merge commit SHA, tests added, review findings and how each was answered.
