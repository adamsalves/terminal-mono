#!/usr/bin/env python3
"""Assert every palette in terminal.css is legible, and stays legible.

Three properties, checked over the five palettes at once:

  contrast  Every token the stylesheet uses as a text color clears WCAG AA
            against every ground the palette declares. All of it is read at
            12-16px, so the threshold is 4.5:1 rather than the 3:1 that large
            text gets, and the worst case is --surface-2 -- the *lightest* of
            the four grounds -- not --bg.

  ramp      --dim < --dim-2 < --muted-2 < --muted < --prose < --soft < --text
            by relative luminance. The names promise an ordering and this is
            what enforces it. It is not decoration: lifting amber's --dim far
            enough to pass AA pushed it past --dim-2, which is a palette that
            passes the contrast half while contradicting its own token names.

  measured  Every token the first two properties need is written in a form
            this can put a number on, and every ground the stylesheet declares
            is one of the grounds it compares against. Both are how the check
            rots into a green run that looked at nothing -- see `unmeasurable`
            and GROUNDS below.

The point is the same one hugo.toml's mount check makes -- a sixth palette is
supposed to be a list of hex values, and this is what stops one from entering
the theme with a rung that fails. It reads the stylesheet and nothing else, so
it needs no build, no browser and no network.

Run: python3 scripts/check_contrast.py [path/to/terminal.css]
"""

import pathlib
import re
import sys

PALETTES = ["lime", "amber", "cyberpunk", "ice", "mono"]

# Every background a palette declares. A text token has to clear all four,
# because nothing in the stylesheet stops --dim from being read on --surface-2.
# check() asserts this list is still the whole set: it is written by hand while
# the text tokens are discovered, so a --surface-4 added to the stylesheet
# would otherwise enter every palette with nothing measured against it.
GROUNDS = ["bg", "surface", "surface-2", "surface-3"]

# The ordering the token names promise, dimmest first.
RAMP = ["dim", "dim-2", "muted-2", "muted", "prose", "soft", "text"]

MIN_RATIO = 4.5

# The two forms this check can measure. Anything else -- rgb(), hsl(),
# color-mix(), a var() indirection, currentColor -- is a value it has to
# refuse out loud rather than walk past, and #rrggbbaa is the reason the
# alternation is exact rather than a {3,8} count: it used to arrive at
# relative_luminance(), lose its alpha in silence and come back as a
# plausible number for a color the stylesheet does not have.
HEX = re.compile(r"#(?:[0-9a-f]{3}|[0-9a-f]{6})")

# Palette blocks carry prose, and a comment can hold anything that would
# otherwise read as a declaration.
COMMENT = re.compile(r"/\*.*?\*/", re.S)

# Tokens that appear in a `color:` declaration and are exempt, with the reason.
# Anything not listed here is checked, so a new text token is covered the day
# it is written rather than the day someone remembers to add it.
EXEMPT = {
    "bg": (
        "only ever text on top of --accent (.skip-link, .btn--solid), so the "
        "pair that matters is --accent against --bg, which is checked as --accent"
    ),
    "border": (
        ".social .sep and .post-meta .sep are punctuation between items, and "
        ".pager .disabled is an inactive control -- WCAG 1.4.3 exempts both"
    ),
}


class Abort(SystemExit):
    def __init__(self, message):
        super().__init__("\033[31maborted:\033[0m %s" % message)


def measurable(value):
    """Whether check() can put a number on this declaration's value."""
    return bool(HEX.fullmatch(value.strip().lower()))


def relative_luminance(hex_color):
    """WCAG 2.x relative luminance for a #rgb or #rrggbb string."""
    h = hex_color.strip().lower()
    if not HEX.fullmatch(h):
        # Only a caller that skipped measurable() gets here, and the point of
        # raising is that it stays a crash rather than becoming a number.
        raise ValueError("cannot measure %r: not a #rgb or #rrggbb color"
                         % hex_color)
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
              for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a, b):
    lighter, darker = sorted((relative_luminance(a), relative_luminance(b)),
                             reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def palette_block(css, palette):
    """The declarations inside one palette's rule, or None if it has none.

    lime is the bare :root -- it is the default, so a site that configures
    nothing gets it -- and the other four are the [data-palette] blocks that
    baseof.html stamps onto <html>.
    """
    head = ":root{" if palette == "lime" else ':root[data-palette="%s"]{' % palette
    if head not in css:
        return None
    return css.split(head, 1)[1].split("}", 1)[0]


def tokens(css, palette):
    """A palette's declarations, resolved over lime, values kept as written.

    A palette restates only what it changes, so everything it leaves out is
    inherited from :root -- the same way the cascade resolves it in a browser.

    Nothing is filtered on the way in, and that is the whole of it. Reading
    only the values that already looked like hex was how a token went
    unchecked in silence: a --dim written rgb(106,106,106) never entered the
    dict, the loop below skipped it for being absent, and a stylesheet that
    fails AA came back clean. Deciding what can be measured is check()'s job,
    out loud, one failure per token.
    """
    resolved = {}
    for source in (["lime"] if palette == "lime" else ["lime", palette]):
        block = palette_block(css, source)
        if block is None:
            return None
        block = COMMENT.sub(" ", block)
        resolved.update({m.group(1): m.group(2).strip().lower() for m in
                         re.finditer(r"--([a-z0-9-]+):\s*([^;}]+)", block)})
    return resolved


def text_tokens(css):
    """Tokens the stylesheet actually reads as a text color, minus the exempt.

    The lookbehind is what keeps `background-color:` and `border-color:` out.
    Today every one of those names a token that is a text color somewhere else
    too, so the difference is invisible -- until the first
    `background-color:var(--surface-2)`, which would enter here as a text
    token and be measured against itself at 1:1.
    """
    used = set(re.findall(r"(?<![-\w])color:\s*var\(--([a-z0-9-]+)\)", css))
    return sorted(used - set(EXEMPT))


def check(css_path):
    try:
        css = pathlib.Path(css_path).read_text()
    except OSError as error:
        raise Abort("cannot read %s: %s" % (css_path, error.strerror))
    failures = []

    checked = text_tokens(css)
    if not checked:
        # A rename, a reformat or a bad path leaves this empty, and an empty
        # loop below is a green check that verified nothing.
        return ["%s: found no `color:var(--…)` declarations at all -- the "
                "stylesheet moved or its shape changed, and this check was "
                "about to pass without looking at anything" % css_path]

    for palette in PALETTES:
        tk = tokens(css, palette)
        if tk is None:
            failures.append("%s: terminal.css declares no block for it" % palette)
            continue

        # A value this check cannot measure is a failure, not a skip. Skipping
        # it is invisible twice over: the text token goes unchecked, and a
        # *ground* that drops out of the comparison also falls back to lime's
        # value, so the failure line for some other token names a hex this
        # palette never declared.
        unmeasurable = sorted(
            name for name in (set(GROUNDS) | set(RAMP) | set(checked)) & set(tk)
            if not measurable(tk[name]))
        for name in unmeasurable:
            failures.append(
                "%s: --%s is %s, which this check cannot measure -- it reads "
                "#rgb and #rrggbb, so either write the token that way or, if "
                "it is not a text color, take it out of GROUNDS/RAMP or add "
                "it to EXEMPT with the reason" % (palette, name, tk[name]))
        skip = set(unmeasurable)

        # GROUNDS is written by hand; the text tokens are discovered. Nothing
        # else would notice a new background token entering the stylesheet.
        extra = sorted({name for name in tk
                        if name == "bg" or name.startswith("surface")}
                       - set(GROUNDS))
        if extra:
            failures.append(
                "%s: declares --%s, and no text token is measured against it "
                "-- add it to GROUNDS" % (palette, ", --".join(extra)))

        grounds = [(g, tk[g]) for g in GROUNDS if g in tk and g not in skip]
        if not grounds:
            failures.append("%s: declares none of %s" % (palette, ", ".join(GROUNDS)))
            continue

        # "The worst case is --surface-2" is a claim this stylesheet happens to
        # make true, not a law. Every comparison below takes the minimum over
        # all four grounds either way, so this does not change a verdict -- it
        # keeps the docstring, the CHANGELOG and the reasoning that produced
        # these values from quietly ceasing to describe the file.
        lightest = max(grounds, key=lambda pair: relative_luminance(pair[1]))[0]
        if lightest != "surface-2":
            failures.append(
                "%s: --%s is lighter than --surface-2, so it is the worst "
                "ground now -- this check's docstring says --surface-2 is"
                % (palette, lightest))

        for token in checked:
            if token not in tk or token in skip:
                continue
            worst_name, worst_ratio = min(
                ((name, contrast(tk[token], value)) for name, value in grounds),
                key=lambda pair: pair[1])
            if worst_ratio < MIN_RATIO:
                failures.append(
                    "%s: --%s %s is %.2f:1 on --%s %s, below %.1f:1"
                    % (palette, token, tk[token], worst_ratio, worst_name,
                       dict(grounds)[worst_name], MIN_RATIO))

        rung = [(name, tk[name]) for name in RAMP
                if name in tk and name not in skip]
        for (lo_name, lo), (hi_name, hi) in zip(rung, rung[1:]):
            if relative_luminance(lo) >= relative_luminance(hi):
                failures.append(
                    "%s: --%s %s is not darker than --%s %s -- the ramp says it "
                    "should be" % (palette, lo_name, lo, hi_name, hi))

    return failures


def main(argv):
    css_path = argv[1] if len(argv) > 1 else "assets/css/terminal.css"
    failures = check(css_path)
    if failures:
        print("\n".join(failures), file=sys.stderr)
        print("\n%d problem(s). Every text token has to clear %.1f:1 against "
              "--bg, --surface, --surface-2 and --surface-3, and the ramp has "
              "to stay in order." % (len(failures), MIN_RATIO), file=sys.stderr)
        return 1
    print("%s: %d palettes, every text token clears %.1f:1 on every ground, "
          "ramp in order" % (css_path, len(PALETTES), MIN_RATIO))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
