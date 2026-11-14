#!/usr/bin/env python3
"""guard-files: PreToolUse hook for file tools (Read, Edit, Write, MultiEdit, NotebookEdit).

Blocks reading or writing `.env*` files (except `.env.example` / `.env.sample`) and private keys,
and blocks hand edits of lockfiles (they change only through the package manager). Exit 2 with a
reason on stderr blocks the call (Claude Code contract). Stdlib only.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

SECRET = re.compile(r"(^|/)(\.env(\.(?!example$|sample$)[\w.-]+)?|id_(rsa|ed25519|ecdsa)|[^/]+\.(pem|key|p12|pfx))$")
LOCKFILES = {"package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "poetry.lock",
             "bun.lock", "bun.lockb"}
WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch"}


def paths_of(event: dict) -> list[str]:
    tool_input = event.get("tool_input") or {}
    found = [tool_input.get(k) for k in ("file_path", "path", "notebook_path") if tool_input.get(k)]
    return [str(p) for p in found]


def reason_for(tool: str, path: str) -> str | None:
    posix = pathlib.PurePath(path).as_posix()
    if SECRET.search(posix):
        return f"{posix} may hold secrets; it never enters the context (use .env.example)"
    if tool in WRITE_TOOLS and pathlib.PurePath(path).name in LOCKFILES:
        return f"{posix} changes only through the package manager (npm install, uv lock), never by hand"
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool = str(event.get("tool_name", ""))
    for path in paths_of(event):
        why = reason_for(tool, path)
        if why:
            print(f"BLOCKED by guard-files: {why}. Do not work around this; ask the owner.", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
