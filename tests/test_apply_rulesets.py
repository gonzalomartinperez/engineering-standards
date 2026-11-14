"""apply-rulesets.sh against a fake `gh` on PATH (no network)."""
import json
import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import unittest

from helpers import ROOT

SCRIPT = ROOT / "scripts/apply-rulesets.sh"

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys
state_path = os.environ["FAKE_GH_STATE"]
state = json.load(open(state_path))
args = sys.argv[1:]
method = "GET"
if "-X" in args:
    method = args[args.index("-X") + 1]
path = next(a for a in args if a.startswith("repos/"))
state["calls"].append([method, path])
json.dump(state, open(state_path, "w"))
if state.get("list_status") == 403 and method == "GET" and "?" in path:
    sys.stderr.write("gh: Resource not accessible (HTTP 403)\n"); sys.exit(1)
if method in ("PUT", "POST") and state.get("write_status"):
    sys.stderr.write(f"gh: Validation Failed (HTTP {state['write_status']})\n"); sys.exit(1)
if method == "GET" and "?" in path:
    print(json.dumps([{"id": i, "name": rs["name"], "source_type": "Repository"} for i, rs in state["rulesets"].items()]))
elif method == "GET":
    print(json.dumps(state["rulesets"][path.rsplit("/", 1)[1]]))
elif method == "POST":
    print(json.dumps(99) if "--jq" in args else json.dumps({"id": 99}))
'''


def server_copy(name):
    """What the API returns: the stored ruleset plus server-added fields."""
    rs = json.loads((ROOT / "rulesets" / name).read_text())
    rs.update({"id": 1, "source_type": "Repository", "source": "o/r", "_links": {}, "created_at": "x"})
    for rule in rs["rules"]:
        if rule["type"] == "pull_request":
            rule["parameters"]["require_extra_approval_for_unattributed_changes"] = True
            rule["parameters"]["required_reviewers"] = []
    return rs


class ApplyRulesetsTests(unittest.TestCase):
    def setUp(self):
        if not shutil.which("jq"):
            self.skipTest("jq not installed")
        self.tmp = tempfile.TemporaryDirectory()
        self.bin = pathlib.Path(self.tmp.name, "bin")
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        self.state = pathlib.Path(self.tmp.name, "state.json")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, state, *args):
        state.setdefault("calls", [])
        self.state.write_text(json.dumps(state))
        env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "FAKE_GH_STATE": str(self.state)}
        proc = subprocess.run(["bash", str(SCRIPT), "--repo", "o/r", "--flow", "main-only", *args],
                              capture_output=True, text=True, env=env)
        return proc.returncode, proc.stdout + proc.stderr, json.loads(self.state.read_text())["calls"]

    def up_to_date(self):
        return {"rulesets": {"1": server_copy("main-only.json"), "2": server_copy("tags.json")}}

    def test_up_to_date_ignores_server_extras(self):
        code, out, calls = self.run_script(self.up_to_date(), "--check")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("is up to date"), 2)
        self.assertFalse(any(m in ("PUT", "POST") for m, _ in calls))

    def test_missing_ruleset_dry_run_and_check(self):
        state = {"rulesets": {"1": server_copy("main-only.json")}}
        code, out, calls = self.run_script(state)
        self.assertEqual(code, 0)
        self.assertIn("missing  standard-release-tags", out)
        self.assertFalse(any(m in ("PUT", "POST") for m, _ in calls))
        self.assertEqual(self.run_script({"rulesets": {"1": server_copy("main-only.json")}}, "--check")[0], 1)

    def test_apply_updates_changed_and_creates_missing(self):
        changed = server_copy("main-only.json")
        changed["rules"] = [r for r in changed["rules"] if r["type"] != "required_status_checks"]
        code, out, calls = self.run_script({"rulesets": {"1": changed}}, "--apply")
        self.assertEqual(code, 0, out)
        self.assertIn(["PUT", "repos/o/r/rulesets/1"], calls)
        self.assertIn(["POST", "repos/o/r/rulesets"], calls)

    def test_failed_write_exits_non_zero(self):
        code, out, _ = self.run_script({"rulesets": {}, "write_status": 422}, "--apply")
        self.assertEqual(code, 1)
        self.assertIn("FAILED", out)

    def test_forbidden_write_and_list_exit_3(self):
        self.assertEqual(self.run_script({"rulesets": {}, "write_status": 403}, "--apply")[0], 3)
        self.assertEqual(self.run_script({"rulesets": {}, "list_status": 403})[0], 3)


if __name__ == "__main__":
    unittest.main()
