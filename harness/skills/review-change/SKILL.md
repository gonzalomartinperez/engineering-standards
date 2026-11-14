---
name: review-change
description: "Reviews a diff independently for correctness, security, missing tests and standards compliance, reproducing every finding. Use when asked to \"review this PR\", \"check this diff\", \"second look before merge\", or before committing a non-trivial change, even if the author already reviewed it. Not for writing the fix or for style-only feedback."
allowed-tools: Read, Grep, Glob, Bash
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# review-change

Catalog skeleton from engineering-standards (ecosystem 15.5). Repositories copy it to
`.agents/skills/review-change/`, link `.claude/skills/review-change` to it, and tune the commands to their stack.

## Checklist

- [ ] Inputs read (AGENTS.md, the item or diff in scope)
- [ ] Procedure followed with the repository's own commands
- [ ] Evidence collected for every claim
- [ ] Output delivered in the template below

## Procedure

1. Get the diff (`git diff <base>...HEAD` or `gh pr diff <n>`) and the PR description; ignore the author's reasoning.
2. Check correctness, security (injection, secrets, authz), data loss, concurrency, contracts, and that tests exercise the change.
3. Check the standards: workflow hardening, Conventional Commit title, docs and CHANGELOG touched when behaviour changed.
4. Reproduce each finding with a failing test, a command or a quoted line; drop what you cannot reproduce or mark it unverified.
5. Report findings by severity with file:line, scenario and fix.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Findings table (severity, file:line, scenario, fix), then Confidence and Escalate lines.
