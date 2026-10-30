"""Tests for the high-precision pattern table.

Fixture values are assembled at runtime, never written as literals: a scanner
repo full of credential-shaped strings would be flagged by the very scanner it
ships (and by every pre-commit hook that later guards this repo).
"""
import unittest

from secretsurface.patterns import PATTERNS, find_matches, is_placeholder


def akia():
    return "AKIA" + "Q7FZ2M4XB9PLR3TK"


def gh_token():
    return "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"


def openai_key():
    return "sk-" + "proj9Xk2mQ7vL4nR8tB3wZ6yC5uA1sD0fG"


class PatternTests(unittest.TestCase):
    def test_aws_key_is_detected_with_its_pattern_id(self):
        matches = find_matches("id = " + akia() + "\n")
        self.assertEqual([m.pattern_id for m in matches], ["aws-access-key"])

    def test_github_token_is_detected(self):
        matches = find_matches("token: " + gh_token() + "\n")
        self.assertEqual([m.pattern_id for m in matches], ["github-token"])

    def test_generic_sk_key_is_detected(self):
        matches = find_matches("OPENAI_API_KEY=" + openai_key() + "\n")
        self.assertEqual([m.pattern_id for m in matches], ["generic-sk-key"])

    def test_pem_private_key_header_is_detected(self):
        # A real PEM body is many base64 lines; a 6-char "MIIEow" fixture was
        # never a key and is now correctly rejected (see test_pem.py).
        body = "MIIEowIBAAKCAQEA7Zk2mQ7vL4nR8tB3wZ6yC5uA1sD0fGhIjKlMnOpQrStUvWx"
        text = "-----BEGIN " + "RSA PRIVATE KEY-----\n" + body + "\n"
        self.assertEqual([m.pattern_id for m in find_matches(text)],
                         ["private-key-pem"])

    def test_line_numbers_are_one_based_and_accurate(self):
        text = "line one\nline two\nkey=" + akia() + "\nline four\n"
        self.assertEqual([m.line for m in find_matches(text)], [3])

    def test_two_hits_on_different_lines_both_appear(self):
        text = akia() + "\n" + gh_token() + "\n"
        self.assertEqual([m.line for m in find_matches(text)], [1, 2])

    def test_fingerprint_is_four_hex_chars(self):
        matches = find_matches(akia())
        self.assertRegex(matches[0].fingerprint, r"^[0-9a-f]{4}$")

    def test_same_value_yields_same_fingerprint_and_different_value_does_not(self):
        a = find_matches(akia())[0]
        b = find_matches(akia())[0]
        c = find_matches("AKIA" + "ZZZZ2222YYYY3333")[0]
        self.assertEqual(a.fingerprint, b.fingerprint)
        self.assertNotEqual(a.fingerprint, c.fingerprint)

    def test_match_objects_never_carry_the_secret(self):
        secret = akia()
        match = find_matches(secret)[0]
        rendered = repr(match) + str(match)
        self.assertNotIn(secret, rendered)
        self.assertNotIn(secret[4:20], rendered)

    def test_value_length_is_reported_not_the_value(self):
        match = find_matches(akia())[0]
        self.assertEqual(match.value_len, len(akia()))

    def test_every_pattern_carries_an_id_and_a_description(self):
        self.assertGreaterEqual(len(PATTERNS), 5)
        for pattern in PATTERNS:
            self.assertTrue(pattern.id)
            self.assertTrue(pattern.description)


class PlaceholderTests(unittest.TestCase):
    """Precision over recall: a crying-wolf scanner gets uninstalled."""

    def test_redacted_text_is_a_placeholder(self):
        self.assertTrue(is_placeholder("AKIAREDACTEDREDACTED"))

    def test_ellipsis_form_is_a_placeholder(self):
        self.assertTrue(is_placeholder("AKIA..."))

    def test_your_key_here_is_a_placeholder(self):
        self.assertTrue(is_placeholder("AKIAYOUR_KEY_HERE_X"))

    def test_example_and_fake_are_placeholders(self):
        self.assertTrue(is_placeholder("AKIAEXAMPLE1234567"))
        self.assertTrue(is_placeholder("AKIAFAKE123456789"))

    def test_low_entropy_repeated_char_is_a_placeholder(self):
        self.assertTrue(is_placeholder("AKIAAAAAAAAAAAAAAAAA"))

    def test_a_real_looking_value_is_not_a_placeholder(self):
        self.assertFalse(is_placeholder(akia()))

    def test_placeholders_do_not_produce_findings(self):
        self.assertEqual(find_matches("k=AKIA" + "REDACTEDREDACTED"), [])
        self.assertEqual(find_matches("k=AKIA" + "EXAMPLE1234567"), [])


if __name__ == "__main__":
    unittest.main()
