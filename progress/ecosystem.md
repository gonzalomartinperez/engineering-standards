# Ecosystem tracker

Single source for milestone state across the repositories (ecosystem standard 3A and 15A). Updated
only at milestone safe points and when a repository finishes or parks a milestone, through a PR to
this repository. Each repository copies the milestone table into its own
`docs/master-plan/progress.md`; the copies are compared at milestones.

## How to resume (any account, machine or agent; nothing from chat history)

1. Read `docs/master-plan/RESUME.md` in any repository, then this file, then the target repository's
   `docs/master-plan/progress.md`.
2. `git fetch --tags` in the repository; check out `develop` (main-only repositories: `main`) at or
   after the last `checkpoint/M<n>` tag and confirm the last CI run on it is green.
3. Continue with the first unchecked item of the current milestone in that repository's
   `docs/master-plan/roadmap.md`, following the per-PR pipeline (ecosystem 15A) and the
   `resume-refactor` skill (`harness/skills/resume-refactor`).
4. Prompt to paste into a new session in a repository:

   > Read AGENTS.md, docs/master-plan/RESUME.md, gonzalomartinperez/engineering-standards
   > progress/ecosystem.md and docs/master-plan/progress.md. Continue the current milestone from the
   > first unchecked roadmap item, one PR per task, merge only with green ci-gate. Do not ask about
   > decisions already recorded in owner-decisions.md; park anything that needs the owner.

5. Shared CI and templates: consume the latest `v1.x` release of this repository as described in
   [docs/how-to/adopt.md](../docs/how-to/adopt.md).

## Milestones

Legend: `done` (safe point reached, checkpoint tag), `in progress`, `parked` (reason in the repo's
progress.md), `—` (not started). Checkpoint tags are created by the orchestrator, not by repo leads.

| Repository | Flow | M0 Plans | M1 Foundation | M2 Quality net | M3 Phase A | M4 Architecture | M5 Design | M6 Excellence | M7 Release |
|---|---|---|---|---|---|---|---|---|---|
| engineering-standards | main-only (public) | n/a | in progress (`v1.0.0`) | — | — | — | — | — | — |
| portfolio | release | done | in progress | — | — | — | — | — | — |
| portfolio-assistant-api | release | done | in progress | — | — | — | — | — | — |
| portfolio-backoffice | release | done | in progress | — | — | — | — | — | — |
| pequeverso | release | done | in progress | — | — | — | — | — | — |
| pequeverso-assistant-api | release | done | in progress | — | — | — | — | — | — |
| pequeverso-backoffice | release | done | in progress | — | — | — | — | — | — |
| vps-ops | main-only (private) | done | in progress | — | — | — | — | — | — |
| pequeverso-marketing | main-only (private) | done | in progress | — | — | — | — | — | — |
| dropshipping-ops | main-only (private) | done | in progress | — | — | — | — | — | — |

M0 is recorded as done because M1 started only after all plans were merged (OD-70); each
repository's progress.md holds the exact merge evidence.

## M1 exit criteria (ecosystem 3A)

- Every repository on shared CI v1 with a green `ci-gate` (profiles via `classify.yml`).
- One weekly Dependabot PR per repository observed or simulated (template shape proven in
  [ADR 0002](../docs/decisions/0002-dependabot-weekly-group-sandbox-proof.md); final schedule
  observation 2026-11-16).
- Image builds reproducible with SBOM and provenance (repositories that build images).
- Harness: skills layout, review chain, activation-evals skeleton.

## Log

| Date | Repository | Event | Evidence |
|---|---|---|---|
| 2026-11-14 | engineering-standards | Repository created (public), rulesets on `main` and `v*` tags, shared CI v1; release PR #6 (v1.0.0) | PRs #1–#6 |
| 2026-11-14 | dependabot-sandbox | E2 proof run; points 3 and 4 proven, 1 and 2 pending the Monday run | ADR 0002 |
