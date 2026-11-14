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
