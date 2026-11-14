import re
import unittest

from helpers import ROOT


class ReleaseMetadataTests(unittest.TestCase):
    def test_version_has_changelog_section(self):
        version = (ROOT / "VERSION").read_text().strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        changelog = (ROOT / "CHANGELOG.md").read_text()
        self.assertIn("## [Unreleased]", changelog)
        if version != "0.1.0":  # bootstrap version predates the first release section
            self.assertRegex(changelog, rf"(?m)^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$")


if __name__ == "__main__":
    unittest.main()


class ReleaseNotesExtractionTests(unittest.TestCase):
    def test_notes_stop_before_link_references(self):
        import os
        import pathlib
        import subprocess
        import sys
        import tempfile

        from helpers import embedded_script

        script = embedded_script(".github/workflows/release.yml", step_name="Read version and release notes")
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            (t / "VERSION").write_text("1.2.3\n")
            (t / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n## [1.2.3] - 2026-01-01\n\n### Added\n\n- x\n\n"
                                            "## [1.2.2] - 2025-12-01\n\n- old\n\n[1.2.3]: https://example.test\n")
            (t / "s.py").write_text(script)
            env = {**os.environ, "GITHUB_OUTPUT": str(t / "out"), "RUNNER_TEMP": tmp}
            subprocess.run([sys.executable, "-I", str(t / "s.py")], cwd=tmp, env=env, check=True)
            notes = (t / "notes.md").read_text()
            self.assertIn("- x", notes)
            self.assertNotIn("old", notes)
            (t / "CHANGELOG.md").write_text("## [1.2.3] - 2026-01-01\n\n- y\n\n[1.2.3]: https://example.test\n")
            subprocess.run([sys.executable, "-I", str(t / "s.py")], cwd=tmp, env=env, check=True)
            self.assertNotIn("example.test", (t / "notes.md").read_text())
            self.assertIn("has_section=true", (t / "out").read_text())
