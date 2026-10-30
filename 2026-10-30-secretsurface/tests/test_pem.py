"""A PEM header on its own is documentation. A header with a base64 body is a key.

Found on real data: scanning ~/.hermes/skills reported 34 hits that were all the
literal pattern string in skill documentation, not one of which was a key.
Requiring an actual body removes that noise without losing real detection.
"""
import unittest

from secretsurface.patterns import find_matches


def header(kind="RSA"):
    return "-----BEGIN " + kind + " PRIVATE KEY-----"


BODY_LINE = "MIIEowIBAAKCAQEA7Zk2mQ7vL4nR8tB3wZ6yC5uA1sD0fGhIjKlMnOpQrStUvWx"


class PemBodyTests(unittest.TestCase):
    def test_header_alone_is_not_a_finding(self):
        self.assertEqual(find_matches(header() + "\n"), [])

    def test_header_followed_by_base64_body_is_a_finding(self):
        matches = find_matches(header() + "\n" + BODY_LINE + "\n")
        self.assertEqual([m.pattern_id for m in matches], ["private-key-pem"])

    def test_line_number_is_the_header_line_not_the_body(self):
        text = "intro\n" + header() + "\n" + BODY_LINE + "\n"
        self.assertEqual([m.line for m in find_matches(text)], [2])

    def test_body_two_lines_below_still_counts(self):
        text = header() + "\n\\\n" + BODY_LINE + "\n"
        self.assertEqual(len(find_matches(text)), 1)

    def test_short_body_does_not_count(self):
        self.assertEqual(find_matches(header() + "\nshort\n"), [])

    def test_documentation_mentioning_the_marker_still_does_not_fire(self):
        doc = "pattern: " + header() + " -- matched as private-key-pem\n"
        self.assertEqual(find_matches(doc), [])


if __name__ == "__main__":
    unittest.main()
