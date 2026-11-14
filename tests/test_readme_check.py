import unittest

from helpers import load_module

M = load_module(".github/workflows/docs.yml", step_id="readme")

HEADINGS = ["Why", "Highlights", "Architecture", "Quickstart", "Where it runs", "Quality", "Documentation",
            "Ecosystem", "Contributing and security", "Scope and limits", "License"]


def readme(headings=HEADINGS, filler=8, extra=""):
    parts = ["<div align='center'>", "  <h1>Product</h1>", "  <img src='x.svg' alt=\"\" width='56'>", "</div>", extra]
    for h in headings:
        parts += ["", f"## {h}", ""] + [f"Line {i}." for i in range(filler)]
    return "\n".join(parts) + "\n"


class ReadmeCheckTests(unittest.TestCase):
    def test_valid_readme(self):
        self.assertEqual(M.check(readme(), 80, 180), [])

    def test_usage_alternatives(self):
        self.assertEqual(M.check(readme([h if h != "Where it runs" else "Usage" for h in HEADINGS]), 80, 180), [])
        self.assertEqual(M.check(readme([h if h != "Where it runs" else "Demo / Proof" for h in HEADINGS]), 80, 180), [])

    def test_missing_heading(self):
        errors = M.check(readme([h for h in HEADINGS if h != "Quality"]), 80, 180)
        self.assertTrue(any("Quality" in e for e in errors))

    def test_out_of_order_heading(self):
        swapped = HEADINGS.copy()
        swapped[0], swapped[1] = swapped[1], swapped[0]
        self.assertTrue(M.check(readme(swapped), 80, 180))

    def test_length_bounds(self):
        self.assertTrue(any("lines" in e for e in M.check(readme(filler=1), 80, 180)))
        self.assertTrue(any("lines" in e for e in M.check(readme(filler=30), 80, 180)))

    def test_todo_and_alt(self):
        errors = M.check(readme(extra="TODO fix <img src='a.png'>"), 80, 180)
        self.assertTrue(any("TODO" in e for e in errors))
        self.assertTrue(any("alt" in e for e in errors))

    def test_too_many_badges(self):
        badges = "".join(f"<img alt='CI' src='b{i}.svg'>" for i in range(4))
        self.assertTrue(any("badges" in e for e in M.check(readme(extra=badges), 80, 180)))

    def test_headings_in_code_blocks_ignored(self):
        text = readme().replace("## Why", "```\n## Why\n```\n\n## Why", 1)
        self.assertEqual(M.check(text, 80, 180), [])


class ReadmeTemplateTests(unittest.TestCase):
    def test_both_variants_have_the_required_headings(self):
        from helpers import ROOT
        for variant in ("public", "private"):
            with self.subTest(variant=variant):
                text = (ROOT / f"templates/readme/README.{variant}.md").read_text(encoding="utf-8")
                self.assertEqual(M.check(text, 0, 180), [])


class ReadmeMainTests(unittest.TestCase):
    def _main(self, text):
        import contextlib
        import io
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "README.md")
            if text is not None:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
            env = {"README_PATH": path, "MIN_LINES": "80", "MAX_LINES": "180"}
            old = {k: os.environ.get(k) for k in env}
            os.environ.update(env)
            try:
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    code = M.main()
            finally:
                for k, v in old.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
            return code, out.getvalue()

    def test_main_passes_valid_readme(self):
        self.assertEqual(self._main(readme())[0], 0)

    def test_main_fails_with_annotations(self):
        code, out = self._main(readme(filler=1))
        self.assertEqual(code, 1)
        self.assertIn("::error file=", out)

    def test_main_missing_readme(self):
        self.assertEqual(self._main(None)[0], 1)


if __name__ == "__main__":
    unittest.main()
