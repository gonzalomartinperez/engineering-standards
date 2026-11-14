# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `classify` reusable workflow: CI profiles from changed files, branch and labels using the caller's `.github/ci-profile.json`; fail-closed (ecosystem 6.0).
- `ci-gate` composite action: the single required check, fail-closed aggregation of `needs`.
- Own CI with self-tests of the reusable workflow and action, and unit tests for the classify and gate logic and the workflow hardening policy.
- Repository bootstrap: license, community files, PR and issue templates, Dependabot weekly group, lint configuration.
