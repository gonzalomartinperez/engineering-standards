"""Shared helpers: load workflow/action YAML and extract embedded `shell: python` scripts."""
from __future__ import annotations

import pathlib
import types

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_yaml(rel: str) -> dict:
    with open(ROOT / rel, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _steps(doc: dict):
    if "runs" in doc:  # composite action
        yield from doc["runs"].get("steps", [])
    for job in (doc.get("jobs") or {}).values():
        yield from job.get("steps", []) or []


def embedded_script(rel: str, step_id: str | None = None, step_name: str | None = None) -> str:
    for step in _steps(load_yaml(rel)):
        if step.get("shell") != "python":
            continue
        if (step_id and step.get("id") == step_id) or (step_name and step.get("name") == step_name):
            return step["run"]
    raise LookupError(f"no python step {step_id or step_name} in {rel}")


def load_module(rel: str, step_id: str | None = None, step_name: str | None = None) -> types.ModuleType:
    """Execute an embedded script as a module (its `if __name__ == '__main__'` block does not run)."""
    module = types.ModuleType(f"embedded_{step_id or step_name}")
    exec(compile(embedded_script(rel, step_id, step_name), rel, "exec"), module.__dict__)  # noqa: S102
    return module
