import contextlib
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

from helpers import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import activation_evals as A  # noqa: E402
import check_skills as C  # noqa: E402


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = fn(*args)
    return code, out.getvalue()


class CheckSkillsTests(unittest.TestCase):
    def test_catalog_is_valid(self):
        code, out = quiet(C.main, ["--skills", str(ROOT / "harness/skills"), "--today", "2026-11-14"])
        self.assertEqual(code, 0, out)

    def test_core_catalog_complete(self):
        names = {p.name for p in (ROOT / "harness/skills").iterdir() if p.is_dir()}
        self.assertLessEqual({"implement-task", "review-change", "verify-release", "update-dependencies",
                              "write-adr", "resume-refactor", "score-repo"}, names)

    def _copy(self, tmp, name="write-adr"):
        dst = pathlib.Path(tmp, ".agents/skills", name)
        shutil.copytree(ROOT / "harness/skills" / name, dst)
        return dst

    def test_stale_and_bad_name_and_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            sd = self._copy(tmp)
            text = (sd / "SKILL.md").read_text()
            (sd / "SKILL.md").write_text(text.replace("name: write-adr", "name: Write_ADR").replace("Not for", "Except"))
            code, out = quiet(C.main, ["--skills", str(sd.parent), "--today", "2027-12-01"])
            self.assertEqual(code, 1)
            self.assertIn("must equal the directory name", out)
            self.assertIn("Not for", out)
            self.assertIn("older than 180 days", out)

    def test_trigger_eval_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            sd = self._copy(tmp)
            data = json.loads((sd / "evals/triggers.json").read_text())
            data["queries"] = data["queries"][:5]
            (sd / "evals/triggers.json").write_text(json.dumps(data))
            code, out = quiet(C.main, ["--skills", str(sd.parent), "--today", "2026-11-14"])
            self.assertEqual(code, 1)
            self.assertIn("at least 10 queries", out)

    def test_claude_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            sd = self._copy(tmp)
            links = pathlib.Path(tmp, ".claude/skills")
            links.mkdir(parents=True)
            args = ["--skills", str(sd.parent), "--claude-links", str(links), "--today", "2026-11-14"]
            self.assertEqual(quiet(C.main, args)[0], 1)
            os.symlink("../../.agents/skills/write-adr", links / "write-adr")
            code, out = quiet(C.main, args)
            self.assertEqual(code, 0, out)
            os.symlink("../../.agents/skills/gone", links / "gone")
            self.assertEqual(quiet(C.main, args)[0], 1)


class ActivationEvalTests(unittest.TestCase):
    ROWS = [
        {"query": "a", "should_trigger": True, "split": "validation", "runs": [True, True, False]},
        {"query": "b", "should_trigger": True, "split": "validation", "runs": [False, False, True]},
        {"query": "c", "should_trigger": False, "split": "validation", "runs": [False, False, False]},
        {"query": "d", "should_trigger": False, "split": "train", "runs": [True, True, True]},
    ]

    def test_score_uses_validation_only(self):
        s = A.score(self.ROWS)
        self.assertEqual(s["queries"], 3)
        self.assertEqual(s["recall"], 0.5)
        self.assertEqual(s["precision"], 1.0)

    def test_compare_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, cand = pathlib.Path(tmp, "b.json"), pathlib.Path(tmp, "c.json")
            base.write_text(json.dumps({"results": self.ROWS}))
            worse = [dict(r, runs=[False, False, False]) if r["query"] == "a" else r for r in self.ROWS]
            cand.write_text(json.dumps({"results": worse}))
            self.assertEqual(quiet(A.main, ["compare", str(base), str(cand)])[0], 1)
            self.assertEqual(quiet(A.main, ["compare", str(base), str(base)])[0], 0)


if __name__ == "__main__":
    unittest.main()
