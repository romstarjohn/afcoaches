import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import backlog  # noqa: E402

BASE = dict(
    summary="s",
    reference="r",
    scope_hint="sh",
    acceptance_hint="ah",
    notes=None,
    deferred_from=None,
    defer_reason=None,
    findings=None,
    direction_hint=None,
)


class BacklogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.paths = backlog.Paths(self.root)
        backlog.init_next_id(self.paths)

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, title, slug, **extra):
        return backlog.create_doc(self.paths, {**BASE, "title": title, "slug": slug, **extra}, None, "2026-11-17")

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = backlog.main(["--root", str(self.root), *argv])
        return code, out.getvalue(), err.getvalue()

    def test_ids_are_sequential_and_zero_padded(self):
        a = self.create("First item", "first-item")
        b = self.create("Second item", "second-item")
        self.assertEqual(a.name, "000001-first-item.md")
        self.assertEqual(b.name, "000002-second-item.md")
        self.assertEqual(self.paths.next_id_file.read_text().strip(), "3")

    def test_init_next_id_respects_existing_docs(self):
        tmp2 = tempfile.TemporaryDirectory()
        self.addCleanup(tmp2.cleanup)
        paths = backlog.Paths(Path(tmp2.name))
        paths.closed_dir.mkdir(parents=True)
        (paths.closed_dir / "000041-old.md").write_text("# Backlog: old\n")
        self.assertEqual(backlog.init_next_id(paths), 42)

    def test_alloc_skips_ids_already_on_disk(self):
        (self.paths.open_dir / "000005-manual.md").write_text("# Backlog: manual\n")
        self.assertEqual(backlog.alloc_id(self.paths), "000006")

    def test_missing_next_id_errors(self):
        self.paths.next_id_file.unlink()
        with self.assertRaises(backlog.BacklogError):
            backlog.alloc_id(self.paths)

    def test_invalid_slug_and_missing_fields(self):
        with self.assertRaises(backlog.BacklogError):
            self.create("x", "Bad_Slug")
        with self.assertRaises(backlog.BacklogError):
            self.create("x", "ok", summary="  ")

    def test_deferred_context_all_or_nothing(self):
        with self.assertRaises(backlog.BacklogError):
            self.create("x", "x", deferred_from="docs/tasks/1.md")
        doc = self.create(
            "x", "x", deferred_from="docs/tasks/1.md", defer_reason="time", findings="f", direction_hint="d"
        )
        text = doc.read_text()
        self.assertIn("## Deferral Context", text)
        self.assertIn("### Direction Hint\n\nd", text)

    def test_find_duplicates_only_open_and_ranked(self):
        a = self.create("Import West African food table", "import-west-african-food-table")
        self.create("Coach onboarding email", "coach-onboarding-email")
        hits = backlog.find_duplicates(self.paths, "Import food table West Africa", "import-food-table")
        self.assertEqual([p for _, p in hits], [a])
        backlog.close_doc(self.paths, a, "done", "imported", None, "2026-11-18")
        self.assertEqual(backlog.find_duplicates(self.paths, "Import food table West Africa", "import-food-table"), [])

    def test_template_is_ignored(self):
        (self.paths.open_dir / "000000-template.md").write_text("# Backlog: Template\n")
        self.assertEqual(backlog.find_duplicates(self.paths, "Template", "template"), [])
        self.assertEqual(backlog.search_by_id(self.paths, "000000", "all"), [])

    def test_close_moves_and_appends_reason(self):
        doc = self.create("Thing", "thing")
        dest = backlog.close_doc(self.paths, doc, "stale", "Superseded by later design", "RFC 2", "2026-11-18")
        self.assertFalse(doc.exists())
        self.assertEqual(dest.parent, self.paths.closed_dir)
        text = dest.read_text()
        self.assertIn("- **Status:** closed\n- **Closed:** 2026-11-18", text)
        self.assertIn("## Close Reason\n\n- **Type:** stale\n\nSuperseded by later design", text)
        self.assertIn("### Close Reference\n\nRFC 2", text)

    def test_cli_roundtrip_with_files_and_id_shorthand(self):
        summary = self.root / "summary.md"
        summary.write_text("Multi\n`code` line\n")
        code, out, _ = self.run_cli(
            "create-doc",
            "--title",
            "CLI item",
            "--slug",
            "cli-item",
            "--summary-file",
            str(summary),
            "--reference",
            "r",
            "--scope-hint",
            "s",
            "--acceptance-hint",
            "a",
            "--auto-id",
        )
        self.assertEqual((code, out.strip()), (0, "docs/backlogs/000001-cli-item.md"))
        self.assertIn("`code` line", (self.root / out.strip()).read_text())

        code, out, _ = self.run_cli("search-by-id", "--id", "000001")
        self.assertEqual(out.strip(), "docs/backlogs/000001-cli-item.md")

        code, out, _ = self.run_cli("close-doc", "--id", "000001", "--type", "done", "--detail", "shipped")
        self.assertEqual((code, out.strip()), (0, "docs/backlogs/closed/000001-cli-item.md"))

        code, _, err = self.run_cli("close-doc", "--id", "000001", "--type", "done", "--detail", "again")
        self.assertEqual(code, 2)
        self.assertIn("found 0", err)

    def test_close_rejects_paths_outside_open_dir(self):
        code, _, err = self.run_cli("close-doc", "--path", "README.md", "--type", "done", "--detail", "x")
        self.assertEqual(code, 2)
        self.assertIn("not an open backlog doc", err)


if __name__ == "__main__":
    unittest.main()
