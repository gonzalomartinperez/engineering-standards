# Contributing

This repository is consumed by nine repositories, so every change is small, tested and released.

## Run the checks

```bash
python3 -m unittest discover -s tests -v
uvx yamllint==1.38.0 -s .
uvx --from actionlint-py==1.7.12.25 actionlint
uvx zizmor==1.32.0 --persona regular .github/workflows actions
```

## Branch flow

Main-only: branch from `main` (`feat/…`, `fix/…`, `chore/…`, `docs/…`), open a PR to `main`, merge with a merge commit only when `ci-gate` is green. No direct pushes.

## Commit and PR convention

- PR titles follow Conventional Commits; the title becomes the merge commit message.
- Any change under `.github/workflows/`, `actions/` or adopter-facing `templates/` adds a `CHANGELOG.md` entry under **Unreleased**.
- Breaking changes to workflow inputs, outputs, job names or template paths are a major version and need an ADR.

## Reporting security issues

See [SECURITY.md](SECURITY.md).
