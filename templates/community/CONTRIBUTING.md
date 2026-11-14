# Contributing

<!-- Skeleton from engineering-standards. Replace every <placeholder>; keep the headings. Not byte-checked by drift. -->

Thanks for helping. This file is short on purpose: run the checks, follow the branch flow, write a Conventional Commit.

## Run the checks

```bash
<one command setup>   # e.g. npm run setup | just setup
<one command check>   # mirrors CI, e.g. npm run check | just check
```

CI runs the same commands through the shared `ci-gate`; a PR merges only when `ci-gate` is green.

## Branch flow

- (Release repo) Branch from `develop` as `feat/…`, `fix/…`, `chore/…`, `docs/…` or `deps/…`; open the PR to `develop`. `main` receives releases only.
- (Main-only repo) Branch from `main`; open the PR to `main`; versions are annotated tags on `main`.
- Keep branches short-lived (five working days at most) and PRs focused on one concern (about 400 changed lines).

## Commit and PR convention

- PR titles follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`); the title becomes the merge commit message.
- Fill in the PR template: summary, linked issue, evidence, docs touched, risk and rollback.
- Dependency updates arrive in one weekly Dependabot PR; do not open separate dependency PRs except for an urgent security fix.

## Reporting security issues

See [SECURITY.md](SECURITY.md). Never open a public issue for a vulnerability.
