# 0003. Release automation of this repository without release-please

- Status: accepted
- Date: 2026-11-14

## Context and problem statement

Ecosystem 3.2 proposes release-please, which needs a GitHub App token or a fine-grained PAT because
pull requests opened with `GITHUB_TOKEN` do not trigger CI, and `main` here requires a green
`ci-gate`. Granting scopes is an owner-only decision (standard 15.4), and the session that built
v1.0.0 could not ask the owner. E5 (release-please on `develop`) is a separate, later sandbox
validation for the release repositories and is not blocked by this repository.

## Considered options

1. release-please with a GitHub App (needs the owner).
2. A version bump in a normal PR (`VERSION` + CHANGELOG section), then `release.yml` on `main` creates
   the tag and an immutable release from that CHANGELOG section.

## Decision outcome

Option 2 for engineering-standards now. The release PR runs the full CI like any other change; the
tag ruleset forbids moving or deleting `v*` tags; immutable releases are enabled on the repository.

### Consequences

- Good: no extra credentials; every release commit passed `ci-gate`; releases are reproducible.
- Bad: the CHANGELOG is curated by hand (the PR template and AGENTS.md require an Unreleased entry).
- Revisit when the owner provides a GitHub App for release-please (parked in the M1 report).

## Confirmation

`tests/test_release.py` requires a CHANGELOG section for the current VERSION; `release.yml` skips
when the release exists.
