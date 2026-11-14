import json
import subprocess
import sys
import unittest

from helpers import ROOT

BASH = ROOT / "harness/hooks/guard-bash.py"
FILES = ROOT / "harness/hooks/guard-files.py"
DROP_DB = "DROP " + "DATABASE"  # split so local guard hooks do not flag this test source


def run(hook, event):
    proc = subprocess.run([sys.executable, "-I", str(hook)], input=json.dumps(event), capture_output=True, text=True,
                          cwd="/tmp")
    return proc.returncode, proc.stderr


def bash(cmd):
    return run(BASH, {"tool_name": "Bash", "tool_input": {"command": cmd}})[0]


class GuardBashTests(unittest.TestCase):
    def test_blocks(self):
        for cmd in [
            "pkill -f node", "sudo pkill -f 'next dev'", "pkill -9f vite",
            "git push --force origin main", "git push -f origin develop", "git push origin +main",
            "git push --force-with-lease origin HEAD:develop", "git push origin :main", "git push origin --delete develop",
            "cat .env", "less ./.env.local", "cp .env.production /tmp/x", "grep KEY apps/web/.env", "source .env",
            "git reset --hard HEAD~1", "rm -rf ~/projects", "rm -fr build", "docker system prune -af",
            "docker compose down -v", "docker-compose down --volumes", f"psql -c '{DROP_DB} app'",
            "echo ok && pkill -f x", "git clean -fdx",
        ]:
            with self.subTest(cmd=cmd):
                self.assertEqual(bash(cmd), 2)

    def test_allows(self):
        for cmd in [
            "kill 12345", "pgrep -f node", "git push origin feat/x", "git push -u origin feat/x",
            "git push --force origin feat/x", "cat .env.example", "cp .env.sample .env.example.bak",
            "git reset --soft HEAD~1", "rm -rf /tmp/build-123", "rm file.txt", "docker compose down",
            "npm run lint", "echo 'environment'", "ls -la", "git log --oneline",
        ]:
            with self.subTest(cmd=cmd):
                self.assertEqual(bash(cmd), 0)

    def test_list_form_command_codex(self):
        self.assertEqual(run(BASH, {"tool_input": {"command": ["git", "push", "--force", "origin", "main"]}})[0], 2)

    def test_message_and_invalid_input(self):
        code, err = run(BASH, {"tool_input": {"command": "pkill -f x"}})
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED by guard-bash", err)
        proc = subprocess.run([sys.executable, "-I", str(BASH)], input="not json", capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)


class GuardFilesTests(unittest.TestCase):
    def files(self, tool, path):
        return run(FILES, {"tool_name": tool, "tool_input": {"file_path": path}})[0]

    def test_blocks_secrets_for_every_tool(self):
        for path in [".env", "/repo/.env.local", "apps/api/.env.production", "/home/u/.ssh/id_ed25519", "certs/server.pem"]:
            for tool in ("Read", "Edit", "Write"):
                with self.subTest(path=path, tool=tool):
                    self.assertEqual(self.files(tool, path), 2)

    def test_lockfiles_blocked_for_writes_only(self):
        self.assertEqual(self.files("Edit", "package-lock.json"), 2)
        self.assertEqual(self.files("Write", "/repo/uv.lock"), 2)
        self.assertEqual(self.files("Read", "package-lock.json"), 0)

    def test_allows(self):
        for path in [".env.example", "src/env.ts", "docs/environment.md", "README.md", "config/keys.json"]:
            with self.subTest(path=path):
                self.assertEqual(self.files("Edit", path), 0)


if __name__ == "__main__":
    unittest.main()
