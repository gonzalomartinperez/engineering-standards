# 0001. ci-gate as a composite action and embedded, tested workflow logic

- Status: accepted
- Date: 2026-11-14
- Deciders: M1 lead (engineering-standards), under DR-03 / E1

## Context and problem statement

Ecosystem standard 6.0–6.1 requires one required check named exactly `ci-gate` and a `classify`
step that picks CI profiles. The shared logic must live in `engineering-standards` and be consumed
by nine repositories pinned by commit SHA. Two constraints shape the design:

1. A job that calls a reusable workflow reports its checks as `<caller job> / <called job>`, so a
   reusable `ci-gate` workflow would surface as `ci-gate / ci-gate`, and rulesets would have to
   require that compound name.
2. A reusable workflow cannot reference its own repository at its own commit (there is no context
   that gives the called workflow's SHA without OIDC), so it cannot call a sibling script or action
   at the same pin without a second, separately bumped pin.

## Decision drivers

- The required check is the literal `ci-gate` in every repository and ruleset.
- One SHA pin per consumer reference; Dependabot bumps it without manual edits elsewhere.
- No third-party action for classification; logic reviewable and unit-tested.

## Considered options

1. `ci-gate` as a reusable workflow; `classify` calls a script at a second pinned ref.
2. `ci-gate` as a composite action used inside a caller job named `ci-gate`; `classify` and the
   other reusable workflows embed their logic as `shell: python` steps that the test suite extracts
   and executes.
3. Publish the logic as a package and install it at run time.

## Decision outcome

Option 2. The caller job is named `ci-gate`, so the check name is exact. Each reusable workflow is
self-contained at its pin; `tests/helpers.py` extracts the embedded scripts and the unit tests run
them (classify, ci-gate, README check, deps guard, vulnerability recorder). `drift.yml` is the only
workflow that checks out this repository, at the commit recorded in the adopter's `standards.lock`.

### Consequences

- Good: exact check name; single pin; logic covered by fast unit tests; no runtime package.
- Bad: logic lives inside YAML; editors give less help. Mitigated by tests and by keeping each
  script under about 200 lines.
- `ci-gate` fails closed: a broken profile map fails `classify`; `expected` makes a skipped job that
  classify selected fail the gate.

## Confirmation

`tests/test_workflow_policy.py` (pins, permissions, harden-runner, no `${{ }}` in `run:`),
`tests/test_classify.py`, `tests/test_ci_gate.py` and the `self-test` job in `ci.yml`, which calls
`./.github/workflows/*.yml` and `./actions/*` from the PR under test.
