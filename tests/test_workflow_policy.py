"""Workflow hardening policy (ecosystem 6.4) for every workflow, composite action and workflow template."""
import re
import unittest

from helpers import ROOT, load_yaml

SHA_USES = re.compile(r"^[\w.-]+/[\w.-]+(/[\w./-]+)?@[0-9a-f]{40}$")
FILES = sorted(
    [p.relative_to(ROOT).as_posix() for p in (ROOT / ".github/workflows").glob("*.yml")]
    + [p.relative_to(ROOT).as_posix() for p in (ROOT / "actions").glob("*/action.yml")]
    + [p.relative_to(ROOT).as_posix() for p in (ROOT / "templates/workflows").glob("*.yml")]
)


def steps_of(doc):
    if "runs" in doc:
        yield None, doc["runs"].get("steps", [])
    for name, job in (doc.get("jobs") or {}).items():
        yield name, job.get("steps") or []


class WorkflowPolicyTests(unittest.TestCase):
    def test_files_found(self):
        self.assertGreater(len(FILES), 2)

    def test_uses_pinned_by_full_sha_with_version_comment(self):
        for rel in FILES:
            lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
            for n, line in enumerate(lines, 1):
                m = re.match(r"^\s*(?:-\s*)?uses:\s*(\S+)(.*)$", line)
                if not m or m.group(1).startswith("./"):
                    continue
                with self.subTest(file=rel, line=n):
                    if rel.startswith("templates/") and m.group(1).endswith("@STANDARDS_SHA"):
                        self.assertTrue(m.group(1).startswith("gonzalomartinperez/engineering-standards/"))
                        self.assertIn("# STANDARDS_TAG", m.group(2))
                        continue
                    self.assertRegex(m.group(1), SHA_USES)
                    self.assertRegex(m.group(2), r"#\s*v?\d", "version comment required after the SHA")

    def test_workflows_start_with_empty_permissions(self):
        for rel in FILES:
            doc = load_yaml(rel)
            if "runs" in doc:
                continue
            with self.subTest(file=rel):
                self.assertEqual(doc.get("permissions"), {}, "top-level `permissions: {}` required")

    def test_no_pull_request_target(self):
        for rel in FILES:
            doc = load_yaml(rel)
            triggers = doc.get(True) or doc.get("on") or {}
            with self.subTest(file=rel):
                self.assertNotIn("pull_request_target", triggers if isinstance(triggers, (dict, list)) else [triggers])

    def test_reusable_workflows_use_configurable_runner(self):
        workflows = sorted((ROOT / ".github/workflows").glob("*.yml"))
        reusable_count = 0
        for path in workflows:
            rel = path.relative_to(ROOT).as_posix()
            doc = load_yaml(rel)
            triggers = doc.get(True) or doc.get("on") or {}
            if not isinstance(triggers, dict) or "workflow_call" not in triggers:
                continue
            reusable_count += 1
            call = triggers["workflow_call"] or {}
            runner = (call.get("inputs") or {}).get("runner") or {}
            with self.subTest(file=rel):
                self.assertEqual(runner.get("type"), "string")
                self.assertEqual(runner.get("default"), "ubuntu-latest")
                self.assertFalse(runner.get("required", False))
            for name, job in (doc.get("jobs") or {}).items():
                with self.subTest(file=rel, job=name):
                    self.assertIn(job.get("runs-on"), (
                        "${{ inputs.runner }}",
                        "${{ inputs.runner || 'ubuntu-latest' }}",
                    ))
        self.assertGreater(reusable_count, 0)

    def test_jobs_have_timeouts_and_explicit_permissions(self):
        for rel in FILES:
            for name, job in (load_yaml(rel).get("jobs") or {}).items():
                with self.subTest(file=rel, job=name):
                    self.assertIn("permissions", job)
                    if "uses" not in job:
                        self.assertIn("timeout-minutes", job)

    def test_harden_runner_first_and_checkout_without_credentials(self):
        for rel in FILES:
            for job, steps in steps_of(load_yaml(rel)):
                if job is None or not steps:
                    continue
                with self.subTest(file=rel, job=job):
                    self.assertTrue(steps[0].get("uses", "").startswith("step-security/harden-runner@"))
                for step in steps:
                    if step.get("uses", "").startswith("actions/checkout@"):
                        with self.subTest(file=rel, job=job, step="checkout"):
                            self.assertIn((step.get("with") or {}).get("persist-credentials"), (False, "false"))

    def test_no_expressions_inside_run_blocks(self):
        for rel in FILES:
            for job, steps in steps_of(load_yaml(rel)):
                for step in steps:
                    with self.subTest(file=rel, job=job, step=step.get("name") or step.get("id")):
                        self.assertNotIn("${{", step.get("run", ""), "pass context through env:")


class TemplateConsistencyTests(unittest.TestCase):
    def test_ci_template_gate_needs_every_job_and_jobs_exist_in_profile(self):
        import json
        doc = load_yaml("templates/workflows/ci.yml")
        jobs = set(doc["jobs"]) - {"ci-gate"}
        self.assertEqual(set(doc["jobs"]["ci-gate"]["needs"]), jobs)
        profile = json.loads((ROOT / "templates/ci-profile/ci-profile.example.json").read_text())
        names = set(profile["base"]) | {j for p in profile["profiles"].values() for j in p.get("adds", [])}
        self.assertLessEqual(jobs - {"classify"}, names)

    def test_own_ci_gate_needs_every_job(self):
        doc = load_yaml(".github/workflows/ci.yml")
        self.assertEqual(set(doc["jobs"]["ci-gate"]["needs"]), set(doc["jobs"]) - {"ci-gate"})


if __name__ == "__main__":
    unittest.main()
