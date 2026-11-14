# Weekly single dependency PR — verified design (2026-11-09)

Owner rule (identical in 7 repos): exactly one dependency PR per repo per week, all ecosystems together, Monday 09:00 America/Argentina/Buenos_Aires (fixed UTC-3, no DST), target `develop`, green CI; manual merge by the owner; promotion to main on demand. If last week's PR is still open, it is updated/superseded, never duplicated. Security-update PRs disabled (repo setting), alerts on, daily vulnerability job records silently in one tracking issue, Monday summary notifies, alert emails as GitHub weekly digest (OD-75); criticals ride the weekly PR (owner accepted).

Mechanism (GitHub docs, verified): `multi-ecosystem-groups` GA since 2025-07-01; group-level `schedule` and `target-branch`; each `updates` entry joins with `multi-ecosystem-group` and `patterns: ["*"]`. Security updates always target the default branch → disabled via Settings ▸ Advanced Security ▸ Dependabot security updates. Default cooldown 3 days since 2026-07-14 (version updates only).

Unverified (must be proven in Phase A with a sandbox repo before rollout): (1) open grouped PR gets updated instead of a new one; (2) day/time/timezone honoured on groups; (3) uv and github-actions accepted in a multi-ecosystem group; (4) cooldown inside groups.

Safety net (always shipped, from the shared standards workflows): `deps-weekly-guard` workflow, Monday 10:30 ART + on Dependabot PR events: asserts ≤ 1 open Dependabot PR; if two, closes the older with a comment pointing to the newer; ensures the PR is up to date with develop (`@dependabot rebase`), and if CI is red, opens/updates a tracking issue and labels the PR `needs-fix` so the agent harness fixes it on the same branch (allowed: pushing fixes to the Dependabot branch disables Dependabot rebases, so the guard recreates instead when superseded).


Verified 2026-11-09 by Dependabot's config validation: `cooldown.semver-major-days` / `semver-minor-days` / `semver-patch-days` are NOT supported for `github-actions` and `docker` (and docker-compose); use only `cooldown.default-days` there. Semver-specific cooldowns apply to package ecosystems (npm, uv, pip).
Also verified 2026-11-09: `open-pull-requests-limit` is rejected on `updates` entries that join a multi-ecosystem group; set `open-pull-requests-limit: 1` on the group (next to `schedule` and `target-branch`).
Also verified 2026-11-09 (zizmor 1.30.1 parser, matching Dependabot docs): `commit-message` may not be set on entries that join a multi-ecosystem group; set it once on the group.
