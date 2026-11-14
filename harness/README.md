# Harness assets

Shared agent-harness files for the ecosystem repositories (ecosystem standard 15).

| Asset | Copy to | Kept in sync by |
|---|---|---|
| `hooks/guard-bash.py`, `hooks/guard-files.py` | `.claude/hooks/` | `standards.lock` (byte-matched) |
| `claude/settings.json` | `.claude/settings.json` (merge with repo-specific allow rules) | review |
| `codex/config.toml` | `.codex/config.toml` (validate against the installed Codex) | review |
| `agents/*.md` | `.claude/agents/` (tune commands to the stack) | review |
| `skills/<name>/` | `.agents/skills/<name>/` plus a relative symlink `.claude/skills/<name>` | `tools/check_skills.py --claude-links` |
| `evals/` | protocol for activation evals | `tools/activation_evals.py` |

Safety hooks and deny rules are repeated in every repository because plugin-provided agents ignore
hooks. Hard rules belong in hooks, not prose.

Guard policy notes: `rm -rf` is allowed on relative paths inside the working tree (for example
`node_modules`, `dist`, `.next`) and on temp directories, and blocked on absolute paths, `~`, `..`,
`.git` and bare `.`/`*`. The hooks fail closed on internal errors. They are best-effort guards that
unwrap common wrappers, not a sandbox; the sandbox and approval policy remain the outer layer.
Skill staleness: `check_skills.py` warns on PRs; a scheduled `--strict-staleness` run belongs to the
M2 eval tooling and is not shipped in v1.0.0.
