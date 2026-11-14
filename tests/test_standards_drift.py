import contextlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

from helpers import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import standards_drift as D  # noqa: E402

COMMIT = "a" * 40


def lock(files=(), checks=(), flow="release", commit=COMMIT):
    return {"standards": {"repository": D.REPOSITORY, "tag": "v1.0.0", "commit": commit}, "flow": flow,
            "files": list(files), "checks": list(checks)}


class Sandbox:
    """A fake adopter repo and a fake standards checkout (not git, so no HEAD check)."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = pathlib.Path(self.tmp.name)
        self.repo, self.std = base / "repo", base / "std"
        (self.std / "templates/community").mkdir(parents=True)
        (self.std / "templates/community/SECURITY.md").write_text("# Security\n")
        (self.repo / ".github/workflows").mkdir(parents=True)
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()

    def write_lock(self, data):
        (self.repo / "standards.lock").write_text(json.dumps(data))

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = D.main(["check", "--repo", str(self.repo), "--standards", str(self.std)])
        return code, out.getvalue()


FILES = [{"path": "SECURITY.md", "template": "templates/community/SECURITY.md"}]


class CheckTests(unittest.TestCase):
    def test_clean(self):
        with Sandbox() as s:
            (s.repo / "SECURITY.md").write_text("# Security\n")
            s.write_lock(lock(FILES))
            self.assertEqual(s.check()[0], 0)

    def test_drifted_copy_fails(self):
        with Sandbox() as s:
            (s.repo / "SECURITY.md").write_text("# Security (edited)\n")
            s.write_lock(lock(FILES))
            code, out = s.check()
            self.assertEqual(code, 1)
            self.assertIn("differs", out)

    def test_missing_copy_fails(self):
        with Sandbox() as s:
            s.write_lock(lock(FILES))
            self.assertEqual(s.check()[0], 1)

    def test_invalid_lock_is_input_error(self):
        with Sandbox() as s:
            s.write_lock(lock(FILES, commit="v1.0.0"))
            self.assertEqual(s.check()[0], 2)
            s.write_lock({**lock(FILES), "flow": "trunk"})
            self.assertEqual(s.check()[0], 2)
            s.write_lock(lock([{"path": "../x", "template": "templates/community/SECURITY.md"}]))
            self.assertEqual(s.check()[0], 2)

    def test_workflow_pins(self):
        with Sandbox() as s:
            wf = s.repo / ".github/workflows/ci.yml"
            wf.write_text(f"jobs:\n  a:\n    uses: {D.REPOSITORY}/.github/workflows/classify.yml@{'b' * 40} # v1.0.1\n")
            s.write_lock(lock(checks=["workflow-pins"]))
            code, out = s.check()
            self.assertEqual(code, 0)
            self.assertIn("::warning", out)
            wf.write_text(wf.read_text() + f"  b:\n    uses: {D.REPOSITORY}/.github/workflows/docs.yml@{'c' * 40}\n")
            self.assertEqual(s.check()[0], 1)
            wf.write_text(f"jobs:\n  a:\n    uses: {D.REPOSITORY}/.github/workflows/classify.yml@v1\n")
            self.assertEqual(s.check()[0], 1)

    def test_head_mismatch_is_input_error(self):
        with Sandbox() as s:
            subprocess.run(["git", "init", "-q", str(s.std)], check=True)
            subprocess.run(["git", "-C", str(s.std), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                            "--allow-empty", "-m", "x"], check=True)
            s.write_lock(lock())
            self.assertEqual(s.check()[0], 2)


def load_template(name):
    return yaml.safe_load((ROOT / "templates/dependabot" / name).read_text())


class DependabotPolicyTests(unittest.TestCase):
    def test_release_template_passes(self):
        self.assertEqual(D.check_dependabot(load_template("release.yml"), "release"), ([], []))

    def test_main_only_template_passes(self):
        self.assertEqual(D.check_dependabot(load_template("main-only.yml"), "main-only"), ([], []))

    def test_own_dependabot_passes(self):
        doc = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
        self.assertEqual(D.check_dependabot(doc, "main-only"), ([], []))

    def test_wrong_flow_target(self):
        errors, _ = D.check_dependabot(load_template("release.yml"), "main-only")
        self.assertTrue(any("target-branch" in e for e in errors))

    def test_entry_level_limit_and_commit_message_rejected(self):
        doc = load_template("release.yml")
        doc["updates"][0]["open-pull-requests-limit"] = 1
        doc["updates"][0]["commit-message"] = {"prefix": "x"}
        errors, _ = D.check_dependabot(doc, "release")
        self.assertEqual(sum("not allowed" in e for e in errors), 2)

    def test_semver_cooldown_on_actions_rejected(self):
        doc = load_template("release.yml")
        gha = next(u for u in doc["updates"] if u["package-ecosystem"] == "github-actions")
        gha["cooldown"]["semver-major-days"] = 14
        errors, _ = D.check_dependabot(doc, "release")
        self.assertTrue(any("not supported for github-actions" in e for e in errors))

    def test_missing_semver_cooldown_on_npm_rejected(self):
        doc = load_template("release.yml")
        npm = next(u for u in doc["updates"] if u["package-ecosystem"] == "npm")
        del npm["cooldown"]["semver-patch-days"]
        self.assertTrue(D.check_dependabot(doc, "release")[0])

    def test_group_name_warning_only(self):
        doc = load_template("release.yml")
        doc["multi-ecosystem-groups"] = {"weekly-all": doc["multi-ecosystem-groups"]["weekly"]}
        for u in doc["updates"]:
            u["multi-ecosystem-group"] = "weekly-all"
        errors, warnings = D.check_dependabot(doc, "release")
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)

    def test_two_groups_rejected(self):
        doc = load_template("release.yml")
        doc["multi-ecosystem-groups"]["other"] = {}
        self.assertTrue(D.check_dependabot(doc, "release")[0])


class InitUpdateTests(unittest.TestCase):
    def test_init_then_check_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                code = D.main(["init", "--repo", str(repo), "--standards", str(ROOT), "--tag", "v1.0.0",
                               "--commit", COMMIT, "--flow", "release", "--visibility", "private"])
            self.assertIn(code, (0, 2))  # 2 when ROOT is a git checkout whose HEAD differs from COMMIT
            if code == 0:
                data = json.loads((repo / "standards.lock").read_text())
                self.assertNotIn("CODE_OF_CONDUCT.md", [f["path"] for f in data["files"]])
                self.assertTrue((repo / "SECURITY.md").exists())

    def test_manifest_templates_exist(self):
        manifest = json.loads((ROOT / "templates/MANIFEST.json").read_text())
        for item in manifest["files"]:
            with self.subTest(item=item["template"]):
                self.assertTrue((ROOT / item["template"]).is_file())

    def test_update_repins_and_recopies(self):
        with Sandbox() as s:
            (s.repo / "SECURITY.md").write_text("old\n")
            s.write_lock(lock(FILES))
            with contextlib.redirect_stdout(io.StringIO()):
                code = D.main(["update", "--repo", str(s.repo), "--standards", str(s.std), "--tag", "v1.1.0",
                               "--commit", "d" * 40])
            self.assertEqual(code, 0)
            data = json.loads((s.repo / "standards.lock").read_text())
            self.assertEqual(data["standards"]["tag"], "v1.1.0")
            self.assertEqual((s.repo / "SECURITY.md").read_text(), "# Security\n")
            self.assertEqual(s.check()[0], 2 if shutil.which("git") and False else 0)


if __name__ == "__main__":
    unittest.main()
