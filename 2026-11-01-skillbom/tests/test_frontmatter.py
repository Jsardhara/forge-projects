import unittest

from skillbom.frontmatter import parse_frontmatter


class FrontmatterBasics(unittest.TestCase):
    def test_name_and_description(self):
        fm = parse_frontmatter(
            '---\nname: arxiv\ndescription: "Search arXiv papers."\n---\n\n# arxiv\n'
        )
        self.assertTrue(fm.ok, fm.problem)
        self.assertEqual(fm.name, "arxiv")
        self.assertEqual(fm.description, "Search arXiv papers.")

    def test_unquoted_value_keeps_inner_colon(self):
        fm = parse_frontmatter("---\nname: x\ndescription: Use when: a fetch fails\n---\n")
        self.assertTrue(fm.ok, fm.problem)
        self.assertEqual(fm.description, "Use when: a fetch fails")

    def test_single_quoted_value(self):
        fm = parse_frontmatter("---\nname: x\ndescription: 'it''s fine'\n---\n")
        self.assertEqual(fm.description, "it's fine")

    def test_inline_tools_list(self):
        fm = parse_frontmatter("---\nname: x\ndescription: d\ntools: [Read, Bash]\n---\n")
        self.assertEqual(fm.tools, ("Read", "Bash"))

    def test_allowed_tools_variant(self):
        fm = parse_frontmatter("---\nname: x\nallowed-tools: [Read]\n---\n")
        self.assertEqual(fm.tools, ("Read",))

    def test_block_tools_list(self):
        text = "---\nname: x\ntools:\n  - Read\n  - Bash\n---\n"
        fm = parse_frontmatter(text)
        self.assertEqual(fm.tools, ("Read", "Bash"))

    def test_nested_metadata_does_not_leak_into_top_level(self):
        text = (
            "---\n"
            "name: x\n"
            "description: d\n"
            "metadata:\n"
            "  hermes:\n"
            "    tags: [Research, Papers]\n"
            "    category: research\n"
            "---\n"
        )
        fm = parse_frontmatter(text)
        self.assertTrue(fm.ok, fm.problem)
        self.assertEqual(fm.name, "x")
        self.assertEqual(fm.tools, ())


class FrontmatterTolerance(unittest.TestCase):
    """Real corpora are not valid YAML. These cases must degrade, never raise."""

    def test_orphan_list_item_after_scalar_key_is_ignored(self):
        # Seen in a real skills store: a scalar key followed by a stray "- path:" line.
        text = "---\nname: google-workspace\ndescription: Workspace.\nplatforms: [linux]\n  - path: scripts/x.py\n- path: scripts/y.py\n---\n"
        fm = parse_frontmatter(text)
        self.assertTrue(fm.ok, fm.problem)
        self.assertEqual(fm.name, "google-workspace")

    def test_missing_frontmatter(self):
        fm = parse_frontmatter("# just a heading\n\nno frontmatter here\n")
        self.assertFalse(fm.ok)
        self.assertIsNone(fm.name)
        self.assertEqual(fm.problem, "no-frontmatter")

    def test_unterminated_frontmatter(self):
        fm = parse_frontmatter("---\nname: x\ndescription: d\n")
        self.assertFalse(fm.ok)
        self.assertEqual(fm.problem, "unterminated-frontmatter")

    def test_empty_text(self):
        fm = parse_frontmatter("")
        self.assertFalse(fm.ok)
        self.assertEqual(fm.problem, "no-frontmatter")

    def test_no_name_key(self):
        fm = parse_frontmatter("---\ndescription: d\n---\n")
        self.assertFalse(fm.ok)
        self.assertEqual(fm.problem, "no-name")

    def test_crlf_frontmatter(self):
        fm = parse_frontmatter("---\r\nname: x\r\ndescription: d\r\n---\r\n")
        self.assertTrue(fm.ok, fm.problem)
        self.assertEqual(fm.name, "x")

    def test_split_lines_never_raises_on_garbage(self):
        for junk in ("---\n:\n:\n:\n---\n", "---\n- a\n- b\n---\n", "---\nname:\n---\n"):
            parse_frontmatter(junk)  # must not raise


if __name__ == "__main__":
    unittest.main()
