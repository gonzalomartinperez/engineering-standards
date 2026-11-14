#!/usr/bin/env python3
"""guard-bash: PreToolUse hook that blocks dangerous shell commands (ecosystem 15.6, OD-74).

Claude Code: register for the Bash tool; the hook reads the event JSON on stdin and exits 2 with a
reason on stderr to block. Codex (`[features] hooks = true`): same script; a list-form command is
joined before matching. Stdlib only. Blocks:
  - `pkill -f` / `pgrep -f | xargs kill` (kill by verified PID only, OD-74)
  - force pushes (`--force`, `-f`, `--force-with-lease`, `+refspec`) that target main or develop,
    or any force push while main or develop is checked out; any push or deletion of main/develop refs
    via `:main`
  - reading or copying `.env` files (`.env.example` and `.env.sample` are allowed)
  - `git reset --hard`, `git clean -fdx`, `rm -rf` outside /tmp, `docker system prune`,
    `docker volume prune`, `docker compose down -v`, `DROP DATABASE`
Hard rules live here, not in prose (ecosystem 15.1). Do not work around a block; ask the owner.
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys

PROTECTED = ("main", "develop")
ENV_FILE = re.compile(r"(^|[/\s'\"=<>])\.env(\.(?!example\b|sample\b)[\w.-]+)?(?=$|[\s'\";|&)<>])")


def command_of(event: dict) -> str:
    tool_input = event.get("tool_input") or {}
    cmd = tool_input.get("command", "")
    if isinstance(cmd, list):
        cmd = " ".join(shlex.quote(str(c)) for c in cmd)
    return str(cmd)


def segments(cmd: str) -> list[list[str]]:
    """Split on ; && || | and newlines, then shell-split each part (best effort)."""
    out = []
    for part in re.split(r"\|\||&&|[;|\n]", cmd):
        try:
            words = shlex.split(part, comments=True)
        except ValueError:
            words = part.split()
        while words and re.fullmatch(r"\w+=.*", words[0]):  # leading VAR=value assignments
            words = words[1:]
        while words and words[0] in ("sudo", "env", "command", "exec", "nohup", "time"):
            words = words[1:]
        if words:
            out.append(words)
    return out


def current_branch() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True,
                              timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def check_git_push(args: list[str]) -> str | None:
    force = any(a in ("--force", "-f", "--force-with-lease", "--force-if-includes") or a.startswith("--force-with-lease=")
                for a in args)
    refspecs = [a for a in args if not a.startswith("-")][1:]  # after the remote
    targets = set()
    for spec in refspecs:
        if spec.startswith("+"):
            force = True
            spec = spec[1:]
        dst = spec.split(":", 1)[1] if ":" in spec else spec
        if spec.startswith(":") and dst.removeprefix("refs/heads/") in PROTECTED:
            return f"deleting a protected branch ({dst}) is blocked"
        targets.add(dst.removeprefix("refs/heads/"))
    if "--delete" in args or "-d" in args:
        if targets & set(PROTECTED):
            return "deleting a protected branch is blocked"
    if not force:
        return None
    if targets & set(PROTECTED):
        return "force push to main or develop is blocked"
    if not refspecs and current_branch() in PROTECTED:
        return "force push while main or develop is checked out is blocked"
    return None


def reason_for(cmd: str) -> str | None:
    if ENV_FILE.search(cmd):
        return "reading or copying .env files is blocked (use .env.example; secrets never enter the context)"
    if re.search(r"\bDROP\s+DATABASE\b", cmd, re.I):
        return "DROP DATABASE is blocked"
    for words in segments(cmd):
        name = words[0].rsplit("/", 1)[-1]
        args = words[1:]
        if name == "pkill" and any(a == "-f" or (a.startswith("-") and not a.startswith("--") and "f" in a) for a in args):
            return "pkill -f is blocked: kill only by verified PID (OD-74)"
        if name == "git" and args:
            sub_i = next((i for i, a in enumerate(args) if not a.startswith("-")), None)
            if sub_i is None:
                continue
            sub, rest = args[sub_i], args[sub_i + 1:]
            if sub == "push":
                why = check_git_push(rest)
                if why:
                    return why
            if sub == "reset" and "--hard" in rest:
                return "git reset --hard is blocked (use git stash or a new branch)"
            if sub == "clean" and any(a.startswith("-") and "f" in a and ("d" in a or "x" in a) for a in rest):
                return "git clean -fd/-fx is blocked"
        if name == "rm" and any(a.startswith("-") and "r" in a.lower() and "f" in a for a in args):
            paths = [a for a in args if not a.startswith("-")]
            if not paths or any(not re.match(r"^(/tmp/|\$TMPDIR/|\$\{TMPDIR\}/|\$RUNNER_TEMP/)", p) for p in paths):
                return "rm -rf outside a temp directory is blocked"
        if name == "docker":
            joined = " ".join(args)
            if re.search(r"\b(system|volume|image|builder)\s+prune\b", joined):
                return "docker prune is blocked"
            if re.search(r"\bcompose\b.*\bdown\b.*(\s-v\b|--volumes)", joined):
                return "docker compose down -v is blocked (it deletes volumes)"
        if name == "docker-compose" and "down" in args and ("-v" in args or "--volumes" in args):
            return "docker compose down -v is blocked (it deletes volumes)"
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0  # not a tool event; nothing to guard
    why = reason_for(command_of(event))
    if why:
        print(f"BLOCKED by guard-bash: {why}. Do not work around this; ask the owner.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
