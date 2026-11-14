# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.0] - 2026-11-14

### Added

- Optional `runner` input on all reusable workflows, defaulting to `ubuntu-latest`, so private repositories can fall back to a self-hosted runner when hosted Actions minutes run out.

## [1.0.0] - 2026-11-14

First release consumed by the ecosystem repositories (M1, decision E1). Adoption guide:
`docs/how-to/adopt.md`.

### Added

- Ecosystem tracker `progress/ecosystem.md` with resume instructions; ADRs 0001 (ci-gate composite and embedded, tested logic), 0002 (Dependabot weekly group sandbox proof, E2) and 0003 (release automation without release-please); adoption and CodeQL guides; `release.yml` that tags `vX.Y.Z` from `VERSION` and the CHANGELOG; README on the ecosystem template, checked by the docs workflow; placeholders for design tokens (M5) and eval tooling (M2).
- `classify` reusable workflow: CI profiles from changed files, branch and labels using the caller's `.github/ci-profile.json`; fail-closed (ecosystem 6.0).
- `ci-gate` composite action: the single required check, fail-closed aggregation of `needs`.
- `security` reusable workflow: zizmor, actionlint, gitleaks and dependency-review (licence allow-list) on PRs.
- `docs` reusable workflow (docs-only fast path): markdownlint-cli2, lychee and the README template check.
- `setup-node` and `setup-python-uv` composite actions: lockfile-keyed caches, `npm ci --ignore-scripts`, `uv sync --locked`.
- `deps-weekly-guard` reusable workflow: at most one open Dependabot PR (older ones closed with a pointer), `needs-fix` label on a red `ci-gate`, silent tracking-issue section; rebase comments opt-in (OD-75).
- `vuln-daily` reusable workflow: osv-scanner (full), compromise watch of workflow actions, optional Grype on deployed digests; updates one tracking issue silently and posts only the Monday summary (OD-75).
- `standards-drift` tool (`tools/standards_drift.py`), `standards.lock` format and schema, `drift` reusable workflow, and `templates/MANIFEST.json` of byte-matched files.
- Dependabot templates for release repos (target `develop`) and main-only repos (target `main`) with the verified group shape, enforced by the `dependabot-policy` drift check.
- Canonical copies of the ecosystem standard, rubrics, Dependabot rule and README template under `standard/`; `ci-profile.json` schema.
- Templates: README (public and private variants) and the shared Ecosystem table, caller workflows (`ci.yml`, `deps-weekly-guard.yml`, `vuln-daily.yml`, `drift.yml`, `scorecard.yml`) and an example `ci-profile.json`.
- Standard rulesets (`rulesets/*.json`) and `scripts/apply-rulesets.sh` (idempotent, dry run by default, `--check` drift mode).
- Harness assets (ecosystem 15): `guard-bash` and `guard-files` hooks (pkill -f, force pushes to protected branches, `.env` and key reads, lockfile hand edits, destructive git/docker/SQL), agent definitions (reviewer, architecture-reviewer, designer-evaluator, test-runner, docs-updater), `.claude/settings.json` and `.codex/config.toml` templates, the seven core skills with trigger and output evals, `check-skills` validator and the activation-evals scorer skeleton.
- Own CI with self-tests of the reusable workflow and action, and unit tests for the classify and gate logic and the workflow hardening policy.
- Repository bootstrap: license, community files, PR and issue templates, Dependabot weekly group, lint configuration.

[Unreleased]: https://github.com/gonzalomartinperez/engineering-standards/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/gonzalomartinperez/engineering-standards/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/gonzalomartinperez/engineering-standards/releases/tag/v1.0.0
