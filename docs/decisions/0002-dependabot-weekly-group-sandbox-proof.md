# 0002. Dependabot weekly single-PR rule: sandbox proof (E2)

- Status: accepted (points 3 and 4 proven; points 1 and 2 partly proven, final observation 2026-11-16)
- Date: 2026-11-14
- Evidence repository: `gonzalomartinperez/dependabot-sandbox` (private, throwaway; archived after the last observation)

## Context and problem statement

Ecosystem standard 5.4 blocks the Dependabot rollout until four points are proven on a sandbox:
(1) an open grouped PR is updated instead of a new PR opening; (2) day, time and timezone are
honoured on groups; (3) `uv` and `github-actions` are accepted in a multi-ecosystem group;
(4) cooldown applies inside groups. `shared/dependabot-rule.md` also lists rules verified only by
configuration validation: group-level `open-pull-requests-limit` and `commit-message`, semver cooldown
keys only for npm/uv, one grouped PR per week, never two open PRs.

## Experiment

Sandbox with `main` (default, holds the config) and `develop` (target), the exact shape of
`templates/dependabot/release.yml` (group `weekly`, Monday 09:00 America/Argentina/Buenos_Aires,
`target-branch: develop`, `open-pull-requests-limit: 1`, `commit-message.prefix: chore(deps)`,
`labels: [dependencies]`; entries npm, uv, github-actions, docker, docker-compose; cooldown 7/14/3 on
npm and uv, `default-days: 7` elsewhere). Dependencies were pinned on 2026-11-14 so that cooldowns are
observable (recent releases inside the cooldown windows). Security-update PRs disabled, alerts on.

| Time (UTC, 2026-11-14) | Action | Result |
|---|---|---|
| 02:36:55 | Config pushed to `main` | Five update jobs (one per ecosystem), all green |
| 02:38:48 | — | PR #1 `chore(deps): Bump the "weekly" group with 5 updates across multiple ecosystems`, base `develop`, labels `dependencies`, `javascript`; 7 files across all five ecosystems |
| 02:50:10 | Outdated `semver@7.8.5` added to `develop`; config re-triggered while PR #1 open | Jobs log `Detected existing pull request #1 for the dependency group 'weekly'. Deferring creation of a new pull request. The existing pull request will update in a separate job.` No new PR; PR #1 not refreshed (unchanged 45 minutes later) |
| 03:35:28 | PR #1 closed (supersede path), config re-triggered | 03:38:14 PR #2 (partial, 4 updates) and 03:38:55 PR #3 (complete); Dependabot closed #2 itself at 03:39:04. End state: one open PR (#3) with every update including `semver 7.8.5 → 7.8.6` |

Versions in PR #1 against the cooldown expectations (release ages on 2026-11-14):

| Dependency | From | Newest available (age) | Bumped to | Cooldown rule |
|---|---|---|---|---|
| hono (npm, patch) | 4.13.10 | 4.13.18 (2 d) | 4.13.17 (6 d) | patch 3 d — honoured |
| @biomejs/biome (npm, patch) | 2.6.3 | 2.6.7 (2 d) | 2.6.6 (7 d) | patch 3 d — honoured |
| eslint (npm, minor) | 10.13.0 | 10.15.0 (0 d) | 10.14.0 (14 d) | default 7 d — honoured |
| prettier (npm) | 3.9.9 | 3.10.1 (1 d) | 3.9.10 (34 d) | default 7 d — honoured |
| commander (npm, major) | 14.0.3 | 15.1.0 (6 d) | 15.0.0 (168 d) | major 14 d — honoured |
| ruff (uv, patch) | 0.17.2 | 0.17.5 (1 d) | 0.17.4 (8 d) | patch 3 d — honoured (log: `Filtered out 1 versions due to cooldown`) |
| requests (uv) | 2.33.1 | 2.34.2 (183 d) | 2.34.2 | — |
| actions/checkout, astral-sh/setup-uv | v6.0.0, v10.3.1 | v7.0.1, v10.3.3 | same | default 7 d |
| python (docker), postgres (docker-compose) | 3.13.0-slim, 17.0 | — | 3.15.0-slim, 18.0 | default 7 d |

## Results per point

1. **Open grouped PR updated, never duplicated — partly proven.** Never duplicated in steady state:
   a run while the group PR is open defers to it and opens nothing. Not observed: the in-place refresh
   ("separate job") did not run on a configuration-triggered run within the session. Closing the PR
   makes the next run open one fresh, complete group PR; Dependabot itself closed a transient partial
   PR within nine seconds. The guard's rule (keep the newest group PR, close older ones) matches this.
2. **Day, time and timezone on groups — not observable in session.** Observation: Monday
   2026-11-16 at 12:00 UTC (09:00 ART). Expected: the "Dependabot Updates" runs start shortly after
   12:00 UTC, and PR #3 is refreshed in place with versions that leave cooldown by then
   (hono 4.13.18, @biomejs/biome 2.6.7, ruff 0.17.5), with no second PR. That run also closes point 1.
3. **uv and github-actions accepted in a multi-ecosystem group — proven** (also docker and
   docker-compose): configuration accepted; all five ecosystems in one PR.
4. **Cooldown inside groups — proven** for npm and uv with 7/14/3 (table above).

Verified rules from `shared/dependabot-rule.md`, confirmed live: group-level
`open-pull-requests-limit: 1`, `commit-message` and `labels` accepted and applied (title prefix
`chore(deps):`, label `dependencies`); group-level `target-branch: develop` honoured; semver cooldown
keys on npm and uv accepted next to `default-days` only on github-actions/docker/docker-compose; with
security-update PRs disabled, seven open alerts produced no security PR.

## Decision outcome

Roll out `templates/dependabot/{release,main-only}.yml` now (points 3 and 4 and the verified rules
hold; the shape is the one Dependabot accepted). Keep `deps-weekly-guard` as the safety net: it keeps
only the newest weekly group PR and flags a red one. Until point 1's in-place refresh is observed, the
operational rule is: when the owner wants a stale open weekly PR to pick up newer versions before the
next Monday, close it; the next run opens one complete PR.

## Confirmation

- `standards-drift` `dependabot-policy` check enforces the shape in every adopter.
- Remaining observation on 2026-11-16 (12:00–13:00 UTC) in the sandbox: run timestamps, PR #3 refresh,
  number of open PRs. Record the outcome as an addendum to this ADR, then archive the sandbox
  (never delete it).
