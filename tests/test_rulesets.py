import json
import subprocess
import unittest

from helpers import ROOT

RULES = ROOT / "rulesets"


class RulesetTests(unittest.TestCase):
    def load(self, name):
        return json.loads((RULES / name).read_text())

    def test_branch_rulesets(self):
        for name, branch in (("release-develop.json", "develop"), ("release-main.json", "main"), ("main-only.json", "main")):
            with self.subTest(ruleset=name):
                rs = self.load(name)
                self.assertEqual(rs["bypass_actors"], [])
                self.assertEqual(rs["enforcement"], "active")
                self.assertEqual(rs["conditions"]["ref_name"]["include"], [f"refs/heads/{branch}"])
                rules = {r["type"]: r.get("parameters", {}) for r in rs["rules"]}
                self.assertLessEqual({"deletion", "non_fast_forward", "pull_request", "required_status_checks"}, set(rules))
                checks = rules["required_status_checks"]
                self.assertEqual(checks["required_status_checks"], [{"context": "ci-gate", "integration_id": 15368}])
                self.assertTrue(checks["strict_required_status_checks_policy"])
                self.assertEqual(rules["pull_request"]["allowed_merge_methods"], ["merge"])

    def test_tag_ruleset(self):
        rs = self.load("tags.json")
        self.assertEqual(rs["target"], "tag")
        self.assertEqual(rs["conditions"]["ref_name"]["include"], ["refs/tags/v*"])
        self.assertEqual({r["type"] for r in rs["rules"]}, {"deletion", "update"})

    def test_script_rejects_bad_arguments_without_network(self):
        script = ROOT / "scripts/apply-rulesets.sh"
        for args in (["--flow", "release"], ["--repo", "a/b", "--flow", "trunk"],
                     ["--repo", "a/b", "--flow", "release", "--merge-methods", "fast-forward"]):
            with self.subTest(args=args):
                proc = subprocess.run(["bash", str(script), *args], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
