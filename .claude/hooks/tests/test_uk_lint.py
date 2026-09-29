#!/usr/bin/env python3
"""Tests for uk-english-lint.py.

Run: python3 .claude/hooks/tests/test_uk_lint.py
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HOOKS, "uk-english-lint.py")


class LintCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp()
        # A product repo and a ticket worktree are nested git checkouts.
        for nested in ("fk-admin-panel-fe", os.path.join(".work", "FKC-1", "fk-mobile")):
            os.makedirs(os.path.join(cls.root, nested))
            open(os.path.join(cls.root, nested, ".git"), "w").close()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def lint(self, rel, text, tool="Write"):
        key = "content" if tool == "Write" else "new_string"
        payload = {"tool_name": tool, "tool_input": {
            "file_path": os.path.join(self.root, rel), key: text}}
        p = subprocess.run(["python3", HOOK], input=json.dumps(payload).encode(),
                           capture_output=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=self.root))
        return p.returncode, p.stderr.decode()

    def flagged(self, text, rel=".work/FKC-1/work.md", tool="Write"):
        code, err = self.lint(rel, text, tool)
        return code == 2

    # --- real hits still caught ---
    def test_prose_caught(self):
        self.assertTrue(self.flagged("We will organize the files."))
        self.assertTrue(self.flagged("The colour is gray."))
        self.assertTrue(self.flagged("Added a robust retry."))
        self.assertTrue(self.flagged("(organize) this."))
        self.assertTrue(self.flagged("**Organize** this."))

    def test_exit_code_and_message(self):
        code, err = self.lint(".work/FKC-1/work.md", "Please organize it.")
        self.assertEqual(code, 2)
        self.assertIn("organize -> -ise", err)

    # --- code-like words skipped ---
    def test_camel_case(self):
        self.assertFalse(self.flagged("| isAuthorized | Boolean |"))
        self.assertFalse(self.flagged("Set centerAlign on the grid."))

    def test_all_caps(self):
        self.assertFalse(self.flagged("Status enum: CANCELED, FULFILLED."))
        self.assertFalse(self.flagged("Use the ORGANIZATION_ID value."))

    def test_punctuated_identifiers(self):
        self.assertFalse(self.flagged("Calls normalizeDate() in src/utils/sanitize.js before save."))
        self.assertFalse(self.flagged("Call sanitize() first."))
        self.assertFalse(self.flagged("See utils/organize for it."))
        self.assertFalse(self.flagged("Set color_mode to dark."))

    # --- non-prose stripped ---
    def test_quoted_strings(self):
        self.assertFalse(self.flagged('Error text: "Unauthorized: token not recognized"'))
        self.assertFalse(self.flagged("The label reads 'Canceled orders'."))
        self.assertTrue(self.flagged("It's the user's job to organize it."))

    def test_blockquote(self):
        self.assertFalse(self.flagged("PO wrote:\n> The status color should be gray.\nOK."))

    def test_frontmatter(self):
        self.assertFalse(self.flagged("---\ndescription: analyze a bug\n---\nBody."))

    def test_html_comment(self):
        self.assertFalse(self.flagged("<!-- organize later -->\nText."))

    def test_code_and_links(self):
        self.assertFalse(self.flagged("Use `normalizeDate()` from `sanitize.js`."))
        self.assertFalse(self.flagged("```\ncolor: red\n```\n"))
        self.assertFalse(self.flagged("    color = 1\n"))
        self.assertFalse(self.flagged("See [the color doc](https://x.y/color)."))

    def test_allow_list(self):
        self.assertFalse(self.flagged("Resize the modal and seize control; citizen size."))

    # --- scope ---
    def test_scope_scanned(self):
        for rel in (".work/FKC-1/work.md", ".claude/guardrails/x.md", "CLAUDE.md",
                    "notes.txt", "docs/repo-map.md"):
            self.assertTrue(self.flagged("optimize the color", rel), rel)

    def test_scope_skipped(self):
        for rel in ("fk-admin-panel-fe/README.md", "fk-admin-panel-be/CHANGELOG.md",
                    ".work/FKC-1/fk-mobile/README.md", ".claude/hooks/x.md",
                    ".claude/skills/plain-uk-english/SKILL.md", "fk-admin-panel-be/src/x.js"):
            self.assertFalse(self.flagged("optimize the color", rel), rel)

    def test_outside_project_skipped(self):
        other = tempfile.mkdtemp()
        try:
            payload = {"tool_name": "Write", "tool_input": {
                "file_path": os.path.join(other, "x.md"), "content": "optimize"}}
            p = subprocess.run(["python3", HOOK], input=json.dumps(payload).encode(),
                               capture_output=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=self.root))
            self.assertEqual(p.returncode, 0)
        finally:
            shutil.rmtree(other)

    # --- edits scan only the new text ---
    def test_edit_scans_new_string_only(self):
        path = os.path.join(self.root, ".work", "FKC-1", "old.md")
        with open(path, "w") as f:
            f.write("An old line we organize.\n")
        payload = {"tool_name": "Edit", "tool_input": {
            "file_path": path, "old_string": "old", "new_string": "new"}}
        p = subprocess.run(["python3", HOOK], input=json.dumps(payload).encode(),
                           capture_output=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=self.root))
        self.assertEqual(p.returncode, 0)
        self.assertTrue(self.flagged("we organize", tool="Edit"))

    def test_multiedit(self):
        payload = {"tool_name": "MultiEdit", "tool_input": {
            "file_path": os.path.join(self.root, ".work", "FKC-1", "m.md"),
            "edits": [{"old_string": "a", "new_string": "fine"},
                      {"old_string": "b", "new_string": "the colour is gray"}]}}
        p = subprocess.run(["python3", HOOK], input=json.dumps(payload).encode(),
                           capture_output=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=self.root))
        self.assertEqual(p.returncode, 2)

    def test_bad_input(self):
        p = subprocess.run(["python3", HOOK], input=b"nope", capture_output=True)
        self.assertEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
