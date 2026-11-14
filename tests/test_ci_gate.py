import json
import unittest

from helpers import load_module

M = load_module("actions/ci-gate/action.yml", step_name="Aggregate job results")


def needs(**results):
    return json.dumps({job: {"result": r} for job, r in results.items()})


class CiGateTests(unittest.TestCase):
    def test_success_and_skipped_pass(self):
        ok, _ = M.evaluate(needs(classify="success", docs="skipped", test="success"), "classify")
        self.assertTrue(ok)

    def test_failure_fails(self):
        self.assertFalse(M.evaluate(needs(classify="success", test="failure"), "classify")[0])

    def test_cancelled_fails(self):
        self.assertFalse(M.evaluate(needs(classify="success", test="cancelled"), "classify")[0])

    def test_required_job_skipped_fails(self):
        self.assertFalse(M.evaluate(needs(classify="skipped", test="success"), "classify")[0])

    def test_required_job_missing_fails(self):
        self.assertFalse(M.evaluate(needs(test="success"), "classify")[0])

    def test_no_required_jobs(self):
        self.assertTrue(M.evaluate(needs(test="skipped"), "")[0])

    def test_empty_needs_fails_closed(self):
        self.assertFalse(M.evaluate("{}", "")[0])

    def test_invalid_json_fails_closed(self):
        self.assertFalse(M.evaluate("not json", "")[0])

    def test_unknown_result_fails(self):
        self.assertFalse(M.evaluate(needs(classify="success", x="neutral"), "classify")[0])


if __name__ == "__main__":
    unittest.main()
