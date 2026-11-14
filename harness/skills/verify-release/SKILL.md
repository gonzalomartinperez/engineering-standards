---
name: verify-release
description: "Verifies a release end to end: release CI profile green, CHANGELOG and version consistent, tag and immutable GitHub Release created, post-deploy checks (build-info SHA, health, version). Use when preparing or checking a develop to main promotion, a release tag or a deploy, even if CI already looks green. Not for day-to-day PRs."
allowed-tools: Read, Grep, Glob, Bash
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# verify-release

Catalog skeleton from engineering-standards (ecosystem 15.5). Repositories copy it to
`.agents/skills/verify-release/`, link `.claude/skills/verify-release` to it, and tune the commands to their stack.

## Checklist

- [ ] Inputs read (AGENTS.md, the item or diff in scope)
- [ ] Procedure followed with the repository's own commands
- [ ] Evidence collected for every claim
- [ ] Output delivered in the template below

## Procedure

1. Confirm the promotion PR ran the `release` profile and `ci-gate` is green.
2. Check `CHANGELOG.md`, the version file and the tag `vX.Y.Z` agree; the release is immutable and carries SBOM and provenance where the repo builds images.
3. After deploy, compare `build-info.json` or `/version` with the merge SHA and run the health and smoke checks.
4. Record the evidence in the release notes and `progress.md`.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Checklist with evidence links (CI run, release URL, build-info SHA, health output).
