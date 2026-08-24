"""Tests for check_contrast.py.

The checker is a guard, so the thing worth testing is that it can still fail.
A parser that quietly matches nothing returns no failures and reads exactly
like a clean stylesheet -- which is the way this check would rot without
anyone noticing, and it is the reason the real terminal.css is one of the
fixtures rather than the only one.
"""

import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_contrast as cc  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent
STYLESHEET = REPO / "assets" / "css" / "terminal.css"


def stylesheet():
    return STYLESHEET.read_text()


class ContrastMath(unittest.TestCase):
    def test_the_extremes(self):
        self.assertAlmostEqual(cc.contrast("#000000", "#ffffff"), 21.0, places=2)
        self.assertAlmostEqual(cc.contrast("#000000", "#000000"), 1.0, places=2)

    def test_it_is_symmetric(self):
        self.assertAlmostEqual(cc.contrast("#798071", "#11140d"),
                               cc.contrast("#11140d", "#798071"), places=6)

    def test_shorthand_hex(self):
        self.assertAlmostEqual(cc.contrast("#fff", "#000"),
                               cc.contrast("#ffffff", "#000000"), places=6)


class Parsing(unittest.TestCase):
    def test_every_palette_resolves(self):
        css = stylesheet()
        for palette in cc.PALETTES:
            with self.subTest(palette=palette):
                tokens = cc.tokens(css, palette)
                self.assertIsNotNone(tokens, "%s has no block" % palette)
                for name in cc.GROUNDS + cc.RAMP:
                    self.assertIn(name, tokens)

    def test_a_palette_inherits_what_it_does_not_restate(self):
        # ice restates no Chroma hues, so it reads lime's -- the same thing the
        # cascade does, and the reason the checker resolves over :root.
        css = stylesheet()
        self.assertEqual(cc.tokens(css, "ice")["code-key"],
                         cc.tokens(css, "lime")["code-key"])

    def test_it_finds_the_text_tokens(self):
        found = cc.text_tokens(stylesheet())
        self.assertIn("dim", found)
        self.assertIn("accent", found)

    def test_the_exempt_tokens_are_still_used_as_text(self):
        # An exemption for a token nothing uses any more is a stale exemption,
        # and the next token to need one gets added next to a lie.
        used = set(cc.text_tokens(stylesheet())) | set(
            re.findall(r"color:\s*var\(--([a-z0-9-]+)\)", stylesheet()))
        for token in cc.EXEMPT:
            with self.subTest(token=token):
                self.assertIn(token, used)


class Verdicts(unittest.TestCase):
    def test_the_shipped_stylesheet_passes(self):
        self.assertEqual(cc.check(STYLESHEET), [])

    def test_it_catches_a_token_below_the_threshold(self):
        css = stylesheet().replace("--dim:#7d7d7d", "--dim:#6a6a6a")
        failures = self.run_on(css)
        self.assertTrue(any("--dim" in f and "mono" in f for f in failures), failures)

    def test_it_catches_an_inverted_ramp(self):
        # Passes AA at 4.54:1 and still wrong: --dim-2 reading darker than --dim.
        css = stylesheet().replace("--dim:#887b67; --dim-2:#95866a",
                                   "--dim:#887b67; --dim-2:#8c7a5c")
        failures = self.run_on(css)
        self.assertTrue(any("ramp" in f for f in failures), failures)

    def test_it_catches_a_missing_palette(self):
        css = stylesheet().replace(':root[data-palette="ice"]{', ":root[data-palette=\"frost\"]{")
        self.assertTrue(any("ice" in f for f in self.run_on(css)))

    def test_a_stylesheet_it_cannot_read_is_a_failure_not_a_pass(self):
        self.assertTrue(self.run_on(":root{--bg:#000}"))

    def run_on(self, css):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as fh:
            fh.write(css)
            path = fh.name
        try:
            return cc.check(path)
        finally:
            pathlib.Path(path).unlink()


if __name__ == "__main__":
    unittest.main()
