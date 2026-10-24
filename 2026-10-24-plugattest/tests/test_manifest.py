"""Tests for plugattest.manifest — declared capabilities across manifest formats."""

import json
import os
import tempfile
import unittest

from plugattest.manifest import load_declared, normalize_capability


def _write(root, relpath, text):
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


class TestNormalizeCapability(unittest.TestCase):
    def test_known_aliases_collapse(self):
        for raw in ("network", "NETWORK", "net", "network.egress", "net:egress"):
            self.assertEqual(normalize_capability(raw), "network")

    def test_fs_aliases(self):
        for raw in ("filesystem", "fs", "fs:write", "file-write", "write"):
            self.assertEqual(normalize_capability(raw), "fs_write")

    def test_unknown_is_returned_lowercased(self):
        self.assertEqual(normalize_capability("telepathy"), "telepathy")


class TestPackageJson(unittest.TestCase):
    def test_capabilities_and_hooks(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({
                "name": "demo",
                "version": "1.0.0",
                "capabilities": ["network", "shell"],
                "scripts": {"postinstall": "node ./setup.js", "test": "jest"},
            }))
            declared = load_declared(root)
        self.assertEqual(set(declared.capabilities), {"network", "shell"})
        self.assertEqual(declared.hooks, ("postinstall",))
        self.assertIn("package.json", declared.sources)

    def test_permissions_key_is_a_declaration(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({
                "name": "demo", "permissions": {"fs:write": "required"},
            }))
            declared = load_declared(root)
        self.assertEqual(set(declared.capabilities), {"fs_write"})

    def test_package_json_without_declaration_key_is_not_a_capability_claim(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "package.json", json.dumps({"name": "demo", "version": "1.0.0"}))
            declared = load_declared(root)
        self.assertEqual(declared.capabilities, ())
        self.assertFalse(declared.declares_capabilities)


class TestPluginJson(unittest.TestCase):
    def test_plugin_json_declares(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, ".claude-plugin/plugin.json", json.dumps({
                "name": "demo", "capabilities": ["credentials"],
            }))
            declared = load_declared(root)
        self.assertEqual(set(declared.capabilities), {"credentials"})
        self.assertIn(".claude-plugin/plugin.json", declared.sources)


class TestSkillFrontmatter(unittest.TestCase):
    def test_inline_list(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "SKILL.md", "---\nname: demo\ncapabilities: [network, shell]\n---\n\nbody\n")
            declared = load_declared(root)
        self.assertEqual(set(declared.capabilities), {"network", "shell"})

    def test_block_list(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "SKILL.md", "---\nname: demo\npermissions:\n  - fs:write\n  - network\n---\nbody\n")
            declared = load_declared(root)
        self.assertEqual(set(declared.capabilities), {"fs_write", "network"})

    def test_frontmatter_without_capability_keys(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "SKILL.md", "---\nname: demo\ndescription: does things\n---\nbody\n")
            declared = load_declared(root)
        self.assertEqual(declared.capabilities, ())
        self.assertEqual(declared.sources, ("SKILL.md",))

    def test_stray_list_item_after_scalar_is_tolerated(self):
        # Real SKILL.md in the wild: a scalar key followed by an orphan "- " line.
        # Tolerate it; never raise, never turn the scalar into a list.
        with tempfile.TemporaryDirectory() as root:
            _write(root, "SKILL.md", (
                "---\nname: demo\ndescription: Google OAuth2 token\n"
                "capabilities: [network]\n- path: google_client_secret.json\n---\nbody\n"
            ))
            declared = load_declared(root)
        self.assertEqual(declared.capabilities, ("network",))

    def test_frontmatter_is_bounded_to_the_first_block(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "SKILL.md",
                   "---\nname: demo\n---\n\ncapabilities: [network]\nnot frontmatter\n")
            declared = load_declared(root)
        self.assertEqual(declared.capabilities, ())


class TestNoManifest(unittest.TestCase):
    def test_empty_dir_has_no_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            declared = load_declared(root)
        self.assertEqual(declared.sources, ())
        self.assertFalse(declared.declares_capabilities)


if __name__ == "__main__":
    unittest.main()
