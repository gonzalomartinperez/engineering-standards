# AGENTS.md — engineering-standards

Central standards for the nine-repo ecosystem: reusable workflows, composite actions, templates,
rulesets, drift tooling, agent-harness assets and the ecosystem tracker. Public repository: **no secrets, ever**.

## Commands (identical to CI)

```bash
python3 -m unittest discover -s tests -v          # unit tests (classify, ci-gate, drift, hooks, skills, policy)
uvx yamllint==1.38.0 -s .                          # YAML lint
uvx --from actionlint-py==1.7.12.25 actionlint     # workflow lint
uvx zizmor==1.32.0 --persona regular .github/workflows actions   # workflow security
shellcheck scripts/*.sh                            # shell lint
npx --yes markdownlint-cli2@0.22.0 "**/*.md"       # Markdown lint
```

## Flow (main-only)

- Branch from fresh `origin/main` as `feat/…`, `fix/…`, `chore/…`, `docs/…`; open a PR to `main`.
- Merge only with green `ci-gate`: `gh pr checks <n> --watch && gh pr merge <n> --merge --delete-branch`. Never `--admin`, never direct pushes, never force-push.
- Releases: bump `VERSION` and move the `CHANGELOG.md` Unreleased section in a PR; `release.yml` tags `vX.Y.Z` on merge.

## Non-negotiables

- Every `uses:` pinned to a full commit SHA with a version comment; `permissions: {}` at workflow top; least privilege per job; `persist-credentials: false`; harden-runner (audit) first; no `pull_request_target`; untrusted context only through `env:`.
- Reusable workflows are a single point of compromise for nine repos: changes need tests, a CHANGELOG entry and a minor or major version bump; breaking input or output changes are a major version.
- `standard/` holds byte-identical canonical copies of the ecosystem standard; edit only through the standards process (ADR + version bump).
- Templates that adopters byte-match are listed in `templates/MANIFEST.json`; changing one is a minor release and adopters receive it through `standards-drift update`.
- Repository docs in English.

## Map

| Path | What |
|---|---|
| `.github/workflows/` | Reusable workflows (`workflow_call`) and this repo's own CI |
| `actions/` | Composite actions (`ci-gate`, `setup-node`, `setup-python-uv`) |
| `templates/` | Files adopters copy (community, GitHub forms, Dependabot, README, CI callers) |
| `tools/` | `standards_drift.py`, `check_skills.py`, `activation_evals.py` (stdlib Python) |
| `rulesets/`, `scripts/apply-rulesets.sh` | Standard rulesets and the idempotent apply script |
| `harness/` | Hooks, agent definitions, Claude settings, Codex config, skill catalog |
| `progress/ecosystem.md` | Ecosystem tracker and resume instructions |
| `docs/decisions/` | ADRs (MADR 4) |
