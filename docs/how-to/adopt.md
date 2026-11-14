# Adopt engineering-standards in a repository

Audience: the M1 lead of an adopter repository (or any agent resuming that work). Every step is a
normal task-branch PR in the adopter repository; nothing here pushes to protected branches.

## 0. Pick the release

```bash
gh release list -R gonzalomartinperez/engineering-standards --limit 5
TAG=v1.0.0                                                   # the latest v1.x
SHA=$(gh api repos/gonzalomartinperez/engineering-standards/commits/$TAG --jq .sha)
ES=$(mktemp -d)                                              # used as $ES below
git clone --depth 1 --branch "$TAG" https://github.com/gonzalomartinperez/engineering-standards.git "$ES"
```

Every reference to this repository is pinned to `$SHA` with `# $TAG` as the comment. Dependabot's
weekly group bumps those pins (github-actions ecosystem) together with everything else.

## 1. CI entry point, profiles and the single required check

1. Copy the caller and the example profile map, then fill in the pins:

   ```bash
   cp $ES/templates/workflows/ci.yml .github/workflows/ci.yml
   cp $ES/templates/ci-profile/ci-profile.example.json .github/ci-profile.json
   sed -i "s/STANDARDS_SHA/$SHA/g; s/STANDARDS_TAG/$TAG/g" .github/workflows/ci.yml
   ```

2. Replace the example `lint`/`test` jobs with the repository's jobs. Rules:
   - every job id is a name in `.github/ci-profile.json` (`base` or a profile's `adds`) and gates on
     `if: contains(fromJSON(needs.classify.outputs.jobs), '<job>')`;
   - `ci-gate.needs` lists every other job; the gate step passes `needs` and `expected`;
   - the required check is the job literally named `ci-gate`.
3. Profile map: every tracked file must fall in a profile (otherwise classify runs everything). Add a
   unit test in the repository asserting that `git ls-files` is covered (pattern: this repository's
   `tests/test_classify.py::OwnProfileMapTests`). Schema:
   `schemas/ci-profile.schema.json`. Built-in profiles: `deps-weekly` (branch `dependabot/**` or
   label `deps-weekly`), `release` (`develop` → `main` or label `release`), `hotfix` (`hotfix/**` →
   `main`); `push`, `schedule`, `workflow_dispatch` and `merge_group` always run everything.

Snippet (job level):

```yaml
  classify:
    uses: gonzalomartinperez/engineering-standards/.github/workflows/classify.yml@<SHA> # <TAG>
    permissions:
      contents: read
      pull-requests: read

  ci-gate:
    if: always()
    needs: [classify, docs, security, lint, test]
    runs-on: ubuntu-latest
    timeout-minutes: 2
    permissions: {}
    steps:
      - uses: step-security/harden-runner@1d88384fd173af6ecb012dfd0264a306b711241a # v2.22.4
        with:
          egress-policy: audit
      - uses: gonzalomartinperez/engineering-standards/actions/ci-gate@<SHA> # <TAG>
        with:
          needs: ${{ toJSON(needs) }}
          expected: ${{ needs.classify.outputs.jobs }}
```

## 2. Security set and docs fast path

Already wired in the `ci.yml` template:

| Job | Reusable workflow | Notes |
|---|---|---|
| `docs` | `docs.yml` | markdownlint, lychee (offline), README template check (the template passes `readme-check: false`; set it to `true` once the README follows the template) |
| `security` | `security.yml` | zizmor, actionlint, gitleaks, dependency-review (`dependency-review: false` on private repos without GHAS) |

The secret scan must run on docs-only PRs: put `security` in `base` (as the example map does) or in the docs profile's `adds`. CodeQL: default setup, see
[codeql.md](codeql.md). Scorecard (public repos): copy `templates/workflows/scorecard.yml` as is.

## 3. Setup actions (step level)

```yaml
      - uses: gonzalomartinperez/engineering-standards/actions/setup-node@<SHA> # <TAG>
        with:
          node-version-file: .nvmrc        # npm ci --ignore-scripts; run-scripts: "true" to opt in
      - uses: gonzalomartinperez/engineering-standards/actions/setup-python-uv@<SHA> # <TAG>
        with:
          sync-args: --all-groups          # uv sync --locked; Python from .python-version
```

Set `cache: "false"` in release or publish jobs.

## 4. Dependabot weekly PR, guard and daily vulnerability job

```bash
FLOW=release   # or main-only for vps-ops, pequeverso-marketing, dropshipping-ops
cp "$ES/templates/dependabot/$FLOW.yml" .github/dependabot.yml
for f in deps-weekly-guard vuln-daily drift; do
  sed "s/STANDARDS_SHA/$SHA/g; s/STANDARDS_TAG/$TAG/g" $ES/templates/workflows/$f.yml > .github/workflows/$f.yml
done
```

- Delete the `updates` entries for ecosystems the repository does not use; add one entry per extra
  manifest directory with the same keys. Never put `open-pull-requests-limit` or `commit-message`
  on an entry, never semver cooldown keys on github-actions/docker/docker-compose.
- Repository settings (owner or lead with admin):
  `gh api -X DELETE repos/gonzalomartinperez/REPO/automated-security-fixes` (security-update PRs off)
  and `gh api -X PUT repos/gonzalomartinperez/REPO/vulnerability-alerts` (alerts on).
- The first scheduled run creates one tracking issue labelled `vuln`; pin it once in the UI. Jobs edit
  it silently; only the Monday run comments (OD-75).
- What was proven about the weekly group and what is still to observe: [ADR 0002](../decisions/0002-dependabot-weekly-group-sandbox-proof.md).

## 5. standards.lock and drift

```bash
python3 $ES/tools/standards_drift.py init --repo . --standards $ES \
  --tag $TAG --flow release --visibility public        # main-only / private as appropriate
uv run --with pyyaml==6.0.3 python $ES/tools/standards_drift.py check --repo . --standards $ES
```

`init` copies the byte-matched files listed in `templates/MANIFEST.json` (SECURITY, SUPPORT, Code of
Conduct on public repos, PR template, issue forms, `docs/master-plan/ecosystem.md`,
`docs/master-plan/rubrics.md`, the guard hooks) and writes `standards.lock`. Review the diff: the
copies replace local versions. After a standards release, check out the new tag into `$ES` and run
`python3 "$ES/tools/standards_drift.py" update --repo . --standards "$ES" --tag vX.Y.Z`. The `drift` workflow fails on any difference and on a Dependabot policy
violation; it warns when workflow pins and the lock disagree.

## 6. Rulesets

Dry run first and read its output (repository admin; release repos protect `develop` and `main`):

```bash
"$ES/scripts/apply-rulesets.sh" --repo gonzalomartinperez/REPO --flow release            # dry run, writes nothing
```

Only after reviewing the dry run:

```bash
"$ES/scripts/apply-rulesets.sh" --repo gonzalomartinperez/REPO --flow release --apply
"$ES/scripts/apply-rulesets.sh" --repo gonzalomartinperez/REPO --flow release --check    # later: drift report
```

Apply only after `ci-gate` exists on the default branches, or every PR blocks. Main-only private
repositories may get exit 3 (rulesets unavailable on the plan): keep the five-layer enforcement of
ecosystem 3.1. `pequeverso-marketing`: `--merge-methods squash`.

## 7. Harness assets

| Asset | Command |
|---|---|
| Hooks | copied by `standards_drift.py init` to `.claude/hooks/`; wire them with `harness/claude/settings.json` (merge your allow rules) |
| Codex | `cp $ES/harness/codex/config.toml .codex/config.toml`, then validate with the installed Codex |
| Agents | `cp $ES/harness/agents/*.md .claude/agents/` and tune the commands |
| Skills | `cp -r $ES/harness/skills/<name> .agents/skills/` and `ln -s ../../.agents/skills/<name> .claude/skills/<name>` |
| Skill check | `python3 $ES/tools/check_skills.py --skills .agents/skills --claude-links .claude/skills` in the harness profile |
