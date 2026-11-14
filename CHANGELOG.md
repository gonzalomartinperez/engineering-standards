# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

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
- Own CI with self-tests of the reusable workflow and action, and unit tests for the classify and gate logic and the workflow hardening policy.
- Repository bootstrap: license, community files, PR and issue templates, Dependabot weekly group, lint configuration.
