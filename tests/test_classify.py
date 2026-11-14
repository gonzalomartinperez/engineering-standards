import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from helpers import ROOT, embedded_script, load_module

WF = ".github/workflows/classify.yml"
M = load_module(WF, step_id="classify")

CONFIG = {
    "base": ["secrets", "markdown"],
    "profiles": {
        "docs": {"paths": ["**/*.md", "docs/**"], "adds": ["links"]},
        "code": {"paths": ["src/**", "package.json"], "adds": ["lint", "unit"]},
        "workflow": {"paths": [".github/**"], "adds": ["actionlint", "zizmor"]},
        "deps-weekly": {"adds": ["all-profiles"]},
        "release": {"adds": ["full-matrix"]},
        "hotfix": {"adds": ["release-verify"]},
    },
}


def pr_event(head="feat/x", base="develop", labels=()):
    return {"pull_request": {"number": 7, "changed_files": 1, "head": {"ref": head}, "base": {"ref": base},
                             "labels": [{"name": n} for n in labels]}}


def run(files, event_name="pull_request", event=None, config=CONFIG):
    def get_files():
        if isinstance(files, Exception):
            raise files
        return files
    return M.classify(config, event_name, event or pr_event(), ".github/ci-profile.json", get_files)


class GlobTests(unittest.TestCase):
    def test_double_star_matches_root_and_nested(self):
        self.assertTrue(M.matches("README.md", ["**/*.md"]))
        self.assertTrue(M.matches("a/b/c.md", ["**/*.md"]))
        self.assertTrue(M.matches("docs/x/y.png", ["docs/**"]))

    def test_single_star_stays_in_segment(self):
        self.assertTrue(M.matches("src/a.ts", ["src/*.ts"]))
        self.assertFalse(M.matches("src/a/b.ts", ["src/*.ts"]))

    def test_literal_dots_are_escaped(self):
        self.assertFalse(M.matches("packageXjson", ["package.json"]))
        self.assertTrue(M.matches("package.json", ["package.json"]))


class ClassifyTests(unittest.TestCase):
    def test_docs_only_fast_path(self):
        r = run(["README.md", "docs/how-to.md"])
        self.assertEqual(r["profile"], "docs")
        self.assertTrue(r["docs-only"])
        self.assertFalse(r["all"])
        self.assertEqual(r["jobs"], ["secrets", "markdown", "links"])

    def test_own_docs_profile_runs_the_secret_scan(self):
        config = json.loads((ROOT / ".github/ci-profile.json").read_text())
        r = M.classify(config, "pull_request", pr_event(), ".github/ci-profile.json", lambda: ["README.md"])
        self.assertTrue(r["docs-only"])
        self.assertIn("security", r["jobs"])

    def test_code_change(self):
        r = run(["src/app.ts", "README.md"])
        self.assertEqual(r["profile"], "code")
        self.assertEqual(r["profiles"], ["code", "docs"])
        self.assertFalse(r["docs-only"])
        self.assertIn("unit", r["jobs"])
        self.assertNotIn("actionlint", r["jobs"])

    def test_unmatched_file_fails_closed(self):
        r = run(["src/app.ts", "Makefile"])
        self.assertTrue(r["all"])
        self.assertEqual(r["profile"], "full")
        self.assertIn("Makefile", r["reason"])
        self.assertIn("actionlint", r["jobs"])
        self.assertIn("full-matrix", r["jobs"])
        self.assertNotIn("all-profiles", r["jobs"])

    def test_diff_error_fails_closed(self):
        r = run(RuntimeError("boom"))
        self.assertTrue(r["all"])
        self.assertIn("boom", r["reason"])

    def test_empty_diff_fails_closed(self):
        self.assertTrue(run([])["all"])

    def test_profile_map_change_fails_closed(self):
        r = run([".github/ci-profile.json"])
        self.assertTrue(r["all"])

    def test_dependabot_branch_runs_everything(self):
        r = run(["package.json"], event=pr_event(head="dependabot/develop/weekly-1234"))
        self.assertEqual(r["profile"], "deps-weekly")
        self.assertTrue(r["all"])

    def test_deps_weekly_label(self):
        self.assertEqual(run(["src/a.ts"], event=pr_event(labels=["deps-weekly"]))["profile"], "deps-weekly")

    def test_release_promotion_runs_everything(self):
        r = run(["src/a.ts"], event=pr_event(head="develop", base="main"))
        self.assertEqual(r["profile"], "release")
        self.assertTrue(r["all"])

    def test_develop_to_other_base_is_not_release(self):
        self.assertEqual(run(["src/a.ts"], event=pr_event(head="develop", base="staging"))["profile"], "code")

    def test_hotfix_adds_without_running_everything(self):
        r = run(["src/a.ts"], event=pr_event(head="hotfix/login", base="main"))
        self.assertEqual(r["profile"], "hotfix")
        self.assertFalse(r["all"])
        self.assertIn("release-verify", r["jobs"])
        self.assertIn("unit", r["jobs"])

    def test_push_runs_everything(self):
        r = run(["src/a.ts"], event_name="push", event={})
        self.assertTrue(r["all"])
        self.assertEqual(r["profile"], "full")

    def test_profile_map_change_with_dot_slash_path(self):
        r = M.classify(CONFIG, "pull_request", pr_event(), "./.github/ci-profile.json", lambda: [".github/ci-profile.json"])
        self.assertTrue(r["all"])

    def test_all_means_every_job(self):
        r = run(["Makefile"])
        expected = ["secrets", "markdown", "links", "lint", "unit", "release-verify", "full-matrix", "actionlint", "zizmor"]
        self.assertEqual(sorted(r["jobs"]), sorted(expected))

    def test_reason_with_control_characters_is_quoted(self):
        r = run(["src/a.ts", "x\rjobs=[]\ry"])
        self.assertTrue(r["all"])
        self.assertNotIn("\r", r["reason"])

    def test_unknown_event_fails_closed(self):
        self.assertTrue(run(["src/a.ts"], event_name="issue_comment", event={})["all"])

    def test_merge_group_runs_everything(self):
        event = {"merge_group": {"head_ref": "refs/heads/gh-readonly-queue/main/pr-1", "base_ref": "refs/heads/main"}}
        r = run(["docs/a.md"], event_name="merge_group", event=event)
        self.assertTrue(r["all"])

    def test_custom_match_conditions(self):
        config = {"base": [], "profiles": {
            "docs": {"paths": ["**/*.md"]},
            "week-close": {"paths": ["retros/**"], "match": [{"labels": ["week-close"]}], "adds": ["scorecard"]},
        }}
        r = run(["README.md"], event=pr_event(labels=["week-close"]), config=config)
        self.assertEqual(r["profiles"], ["docs", "week-close"])
        self.assertIn("scorecard", r["jobs"])


class MainEntryPointTests(unittest.TestCase):
    """Runs the embedded script end to end as the runner would (`python {0}`), without network."""

    def _run_main(self, event_name, event, config):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            (tmp / "event.json").write_text(json.dumps(event))
            cfg = tmp / "ci-profile.json"
            if config is not None:
                cfg.write_text(config if isinstance(config, str) else json.dumps(config))
            (tmp / "script.py").write_text(embedded_script(WF, step_id="classify"))
            env = {**os.environ, "GITHUB_EVENT_NAME": event_name, "GITHUB_EVENT_PATH": str(tmp / "event.json"),
                   "GITHUB_OUTPUT": str(tmp / "out"), "CONFIG_PATH": str(cfg)}
            env.pop("GITHUB_STEP_SUMMARY", None)
            proc = subprocess.run([sys.executable, "-I", str(tmp / "script.py")], env=env, capture_output=True, text=True)
            out = (tmp / "out").read_text() if (tmp / "out").exists() else ""
            return proc.returncode, dict(line.split("=", 1) for line in out.splitlines())

    def test_outputs_written_on_push(self):
        code, out = self._run_main("push", {}, CONFIG)
        self.assertEqual(code, 0)
        self.assertEqual(out["profile"], "full")
        self.assertEqual(out["all"], "true")
        self.assertIn("unit", json.loads(out["jobs"]))

    def test_invalid_config_fails_the_job(self):
        code, out = self._run_main("pull_request", pr_event(), "{not json")
        self.assertEqual(code, 1)
        self.assertEqual(out, {})

    def test_missing_config_fails_the_job(self):
        self.assertEqual(self._run_main("pull_request", pr_event(), None)[0], 1)

    def test_empty_profiles_fails_the_job(self):
        self.assertEqual(self._run_main("pull_request", pr_event(), {"base": ["x"], "profiles": {}})[0], 1)

    def test_profile_without_paths_or_match_fails_the_job(self):
        self.assertEqual(self._run_main("push", {}, {"profiles": {"tools": {"adds": ["x"]}}})[0], 1)


class OwnProfileMapTests(unittest.TestCase):
    """Every tracked file of this repository falls inside a profile (no accidental full runs)."""

    def test_no_tracked_file_outside_profiles(self):
        config = json.loads((ROOT / ".github/ci-profile.json").read_text())
        files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
        paths = [p for spec in config["profiles"].values() for p in spec.get("paths", [])]
        outside = [f for f in files if not M.matches(f, paths)]
        self.assertEqual(outside, [])


if __name__ == "__main__":
    unittest.main()
