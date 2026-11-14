#!/usr/bin/env python3
"""standards-drift: keep an adopter repository in sync with a pinned engineering-standards release.

Commands
  check   Compare the adopter's copies with the pinned standards checkout and run policy checks.
  init    Write a first standards.lock for a repository (files chosen from templates/MANIFEST.json).
  update  Re-pin standards.lock to another release and re-copy every byte-matched file.

The adopter commits `standards.lock` (JSON, schema in schemas/standards-lock.schema.json):

  {
    "standards": {"repository": "gonzalomartinperez/engineering-standards", "tag": "v1.0.0", "commit": "<sha>"},
    "flow": "release",                       # release (develop + main) or main-only
    "files": [{"path": "SECURITY.md", "template": "templates/community/SECURITY.md"}],
    "checks": ["dependabot-policy", "workflow-pins"]
  }

Exit codes: 0 clean, 1 drift or policy failure, 2 usage or input error. Stdlib only, except the
`dependabot-policy` check, which needs PyYAML (`uv run --with pyyaml==6.0.3 ...`).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

REPOSITORY = "gonzalomartinperez/engineering-standards"
KNOWN_CHECKS = {"dependabot-policy", "workflow-pins"}
SEMVER_ECOSYSTEMS = {"npm", "uv", "pip", "bun", "yarn", "pnpm"}
NO_SEMVER_ECOSYSTEMS = {"github-actions", "docker", "docker-compose"}
PIN_RE = re.compile(r"uses:\s*['\"]?" + re.escape(REPOSITORY) + r"/[^@\s'\"]+@([0-9a-f]{40}|[^\s'\"#]+)")


class InputError(Exception):
    """Invalid lock file, arguments or checkout (exit code 2)."""


# ---------------------------------------------------------------- lock file


def load_lock(path: pathlib.Path) -> dict:
    try:
        lock = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputError(f"{path} not found") from exc
    except ValueError as exc:
        raise InputError(f"{path} is not valid JSON: {exc}") from exc
    std = lock.get("standards") or {}
    if std.get("repository") != REPOSITORY:
        raise InputError(f"standards.repository must be {REPOSITORY}")
    if not re.fullmatch(r"v\d+\.\d+\.\d+", str(std.get("tag", ""))):
        raise InputError("standards.tag must look like vX.Y.Z")
    if not re.fullmatch(r"[0-9a-f]{40}", str(std.get("commit", ""))):
        raise InputError("standards.commit must be a full 40-character SHA")
    if lock.get("flow") not in ("release", "main-only"):
        raise InputError("flow must be 'release' or 'main-only'")
    files = lock.get("files", [])
    if not isinstance(files, list) or any(not isinstance(f, dict) or not f.get("path") or not f.get("template") for f in files):
        raise InputError("files must be a list of {path, template}")
    for f in files:
        for key in ("path", "template"):
            p = pathlib.PurePosixPath(f[key])
            if p.is_absolute() or ".." in p.parts:
                raise InputError(f"{key} {f[key]!r} must be a relative path inside the repository")
    checks = lock.get("checks")
    if not isinstance(checks, list) or not checks:
        raise InputError("checks must list the policy checks (dependabot-policy, workflow-pins)")
    unknown = set(checks) - KNOWN_CHECKS
    if unknown:
        raise InputError(f"unknown checks: {', '.join(sorted(unknown))}")
    return lock


def write_lock(path: pathlib.Path, lock: dict) -> None:
    path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- checks


def check_files(repo: pathlib.Path, standards: pathlib.Path, files: list[dict]) -> list[str]:
    problems = []
    for entry in files:
        template, target = standards / entry["template"], repo / entry["path"]
        if not template.is_file():
            problems.append(f"{entry['template']}: not in the pinned standards release")
        elif not target.is_file():
            problems.append(f"{entry['path']}: missing (expected a copy of {entry['template']})")
        elif template.read_bytes() != target.read_bytes():
            problems.append(f"{entry['path']}: differs from {entry['template']} (run `standards_drift.py update` or revert)")
    return problems


def check_dependabot(doc: dict, flow: str) -> tuple[list[str], list[str]]:
    """Validate the verified weekly single-PR shape (ecosystem 5.2, shared/dependabot-rule.md)."""
    errors, warnings = [], []
    if not isinstance(doc, dict):
        return ["the file is not a YAML mapping"], warnings
    if doc.get("version") != 2:
        errors.append("version must be 2")
    groups = doc.get("multi-ecosystem-groups") or {}
    if not isinstance(groups, dict) or len(groups) != 1 or not isinstance(next(iter(groups.values())), dict):
        errors.append(f"exactly one multi-ecosystem group required (found {len(groups)})")
        return errors, warnings
    (name, group), = groups.items()
    if name != "weekly":
        warnings.append(f"group is named {name!r}; the standard name is 'weekly'")
    sched = group.get("schedule") or {}
    expected_sched = {"interval": "weekly", "day": "monday", "time": "09:00", "timezone": "America/Argentina/Buenos_Aires"}
    for key, value in expected_sched.items():
        if str(sched.get(key)) != value:
            errors.append(f"group schedule.{key} must be {value!r} (found {sched.get(key)!r})")
    target = "develop" if flow == "release" else "main"
    if group.get("target-branch") != target:
        errors.append(f"group target-branch must be {target!r} for the {flow} flow")
    if group.get("open-pull-requests-limit") != 1:
        errors.append("group open-pull-requests-limit must be 1")
    if not (group.get("commit-message") or {}).get("prefix"):
        errors.append("group commit-message.prefix is required (set once on the group)")
    updates = doc.get("updates") or []
    if not isinstance(updates, list):
        return errors + ["updates must be a list"], warnings
    ecosystems = set()
    for i, entry in enumerate(updates):
        if not isinstance(entry, dict):
            errors.append(f"updates[{i}] must be a mapping")
            continue
        eco = entry.get("package-ecosystem", f"#{i}")
        ecosystems.add(eco)
        where = f"updates[{i}] ({eco} {entry.get('directory') or entry.get('directories')})"
        if entry.get("multi-ecosystem-group") != name:
            errors.append(f"{where}: must join multi-ecosystem-group {name!r}")
        if entry.get("patterns") != ["*"]:
            errors.append(f"{where}: patterns must be [\"*\"]")
        for key in ("open-pull-requests-limit", "commit-message", "schedule", "target-branch", "groups"):
            if key in entry:
                errors.append(f"{where}: {key} is not allowed on entries that join the group")
        cooldown = entry.get("cooldown") if isinstance(entry.get("cooldown"), dict) else {}
        if cooldown.get("default-days") != 7:
            errors.append(f"{where}: cooldown.default-days must be 7")
        semver_keys = {k for k in cooldown if k.startswith("semver-")}
        if eco in NO_SEMVER_ECOSYSTEMS and semver_keys:
            errors.append(f"{where}: semver cooldown keys are not supported for {eco}")
        if eco in SEMVER_ECOSYSTEMS:
            if cooldown.get("semver-major-days") != 14 or cooldown.get("semver-patch-days") != 3:
                errors.append(f"{where}: cooldown semver-major-days 14 and semver-patch-days 3 required")
    if "github-actions" not in ecosystems:
        errors.append("a github-actions entry is required")
    return errors, warnings


def check_workflow_pins(repo: pathlib.Path, commit: str) -> tuple[list[str], list[str]]:
    errors, warnings, pins = [], [], {}
    for path in sorted((repo / ".github" / "workflows").glob("*.y*ml")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            m = PIN_RE.search(line)
            if m:
                pins.setdefault(m.group(1), []).append(f"{path.relative_to(repo).as_posix()}:{n}")
    for ref, places in pins.items():
        if not re.fullmatch(r"[0-9a-f]{40}", ref):
            errors.append(f"standards reference {ref!r} is not a full SHA ({places[0]})")
    if len(pins) > 1:
        errors.append("standards workflows are pinned to different commits: " + ", ".join(f"{r[:12]} ({v[0]})" for r, v in pins.items()))
    elif pins and commit not in pins:
        warnings.append(f"workflows pin {next(iter(pins))[:12]} but standards.lock pins {commit[:12]}; "
                        "run `standards_drift.py update` after the weekly dependency PR")
    return errors, warnings


def run_check(repo: pathlib.Path, standards: pathlib.Path, lock_path: pathlib.Path) -> int:
    lock = load_lock(lock_path)
    head = git_head(standards)
    if head and head != lock["standards"]["commit"]:
        raise InputError(f"standards checkout is at {head[:12]}, standards.lock pins {lock['standards']['commit'][:12]}")
    errors = check_files(repo, standards, lock["files"])
    warnings: list[str] = []
    if "dependabot-policy" in lock.get("checks", []):
        dep = repo / ".github" / "dependabot.yml"
        if not dep.is_file():
            errors.append(".github/dependabot.yml: missing")
        else:
            try:
                import yaml  # noqa: PLC0415 - optional dependency, only for this check
            except ImportError as exc:
                raise InputError("dependabot-policy needs PyYAML: uv run --with pyyaml==6.0.3 ...") from exc
            try:
                doc = yaml.safe_load(dep.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                raise InputError(f".github/dependabot.yml is not valid YAML: {exc}") from exc
            e, w = check_dependabot(doc, lock["flow"])
            errors += [f".github/dependabot.yml: {x}" for x in e]
            warnings += [f".github/dependabot.yml: {x}" for x in w]
    if "workflow-pins" in lock.get("checks", []):
        e, w = check_workflow_pins(repo, lock["standards"]["commit"])
        errors += e
        warnings += w
    for w in warnings:
        print(f"::warning title=standards-drift::{w}")
    for e in errors:
        print(f"::error title=standards-drift::{e}")
    std = lock["standards"]
    print(f"standards-drift: {std['tag']} ({std['commit'][:12]}), {len(lock['files'])} file(s), "
          f"{len(errors)} problem(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


# ---------------------------------------------------------------- init / update


def git_head(path: pathlib.Path) -> str | None:
    """HEAD of a git checkout; None for a plain directory; InputError when git fails on a checkout."""
    if not (path / ".git").exists():
        return None
    try:
        out = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise InputError(f"cannot read HEAD of {path}: {exc}") from exc
    return out.stdout.strip()


def manifest_files(standards: pathlib.Path, flow: str, visibility: str) -> list[dict]:
    manifest = json.loads((standards / "templates" / "MANIFEST.json").read_text(encoding="utf-8"))
    chosen = []
    for item in manifest["files"]:
        if flow in item.get("flows", ["release", "main-only"]) and visibility in item.get("visibility", ["public", "private"]):
            chosen.append({"path": item["path"], "template": item["template"]})
    return chosen


def copy_files(repo: pathlib.Path, standards: pathlib.Path, files: list[dict]) -> None:
    for entry in files:
        target = repo / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(standards / entry["template"], target)
        print(f"copied {entry['template']} -> {entry['path']}")


def resolve_pin(standards: pathlib.Path, tag: str, commit: str | None) -> str:
    head = git_head(standards)
    commit = commit or head
    if not commit or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise InputError("pass --commit <40-char SHA> (the standards checkout is not a git repository)")
    if head and head != commit:
        raise InputError(f"standards checkout is at {head[:12]}, not {commit[:12]}; check out {tag} first")
    return commit


def run_init(args) -> int:
    lock_path = args.repo / "standards.lock"
    if lock_path.exists() and not args.force:
        raise InputError(f"{lock_path} exists; use update (or --force)")
    commit = resolve_pin(args.standards, args.tag, args.commit)
    files = manifest_files(args.standards, args.flow, args.visibility)
    lock = {"standards": {"repository": REPOSITORY, "tag": args.tag, "commit": commit}, "flow": args.flow,
            "files": files, "checks": ["dependabot-policy", "workflow-pins"]}
    copy_files(args.repo, args.standards, files)
    write_lock(lock_path, lock)
    print(f"wrote {lock_path}")
    return 0


def run_update(args) -> int:
    lock_path = args.repo / "standards.lock"
    lock = load_lock(lock_path)
    commit = resolve_pin(args.standards, args.tag, args.commit)
    lock["standards"].update({"tag": args.tag, "commit": commit})
    missing = [f["template"] for f in lock["files"] if not (args.standards / f["template"]).is_file()]
    if missing:
        raise InputError("templates removed in this release: " + ", ".join(missing))
    copy_files(args.repo, args.standards, lock["files"])
    write_lock(lock_path, lock)
    print(f"standards.lock now pins {args.tag} ({commit[:12]}); review the diff and commit")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="standards-drift", description=(__doc__ or "").split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "init", "update"):
        p = sub.add_parser(name)
        p.add_argument("--repo", type=pathlib.Path, default=pathlib.Path("."), help="adopter repository root")
        p.add_argument("--standards", type=pathlib.Path, required=True, help="checkout of engineering-standards")
        if name == "check":
            p.add_argument("--lock", type=pathlib.Path, default=None, help="lock file (default <repo>/standards.lock)")
        else:
            p.add_argument("--tag", required=True, help="standards release tag, e.g. v1.0.0")
            p.add_argument("--commit", help="commit of the tag (default: HEAD of --standards)")
        if name == "init":
            p.add_argument("--flow", choices=["release", "main-only"], required=True)
            p.add_argument("--visibility", choices=["public", "private"], required=True)
            p.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            return run_check(args.repo, args.standards, args.lock or args.repo / "standards.lock")
        if args.command == "init":
            return run_init(args)
        return run_update(args)
    except InputError as exc:
        print(f"::error title=standards-drift::{exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
