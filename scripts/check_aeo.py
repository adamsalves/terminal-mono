"""Assert the AEO output of a built site: robots.txt and the JSON-LD graph.

Everything this checks fails silently. A robots.txt whose Sitemap line points at
a file that is not in the build still serves 200. A JSON-LD block with a typo in
it still renders — a crawler skips it and the page looks perfect to a human. An
`author` that references an @id no node defines is a graph with a hole in the
middle of it, and no browser will ever say so.

So the build is the fixture and the assertions are the review:

  robots.txt   one Sitemap line, naming a file the build actually published;
               every group carries at least one rule; the four crawlers aeo.js
               calls major are allowed; and an indexable build contains no bare
               `Disallow: /`, which is the line that would silently switch the
               whole site off.

  JSON-LD      every block parses; every page carries a publisher and a WebSite;
               posts carry a BlogPosting with the fields that make it one; every
               @id a node references is defined by a node on the same page; and
               a BreadcrumbList counts 1..n with no gaps and no self-link on its
               last crumb.

Run: python3 scripts/check_aeo.py <public-dir> [--expect-robots] [--indexable]
"""

import json
import pathlib
import re
import sys

# The four aeo.js weighs in its "Major AI bots allowed" check. Being allowed is
# the theme's default; a build where one of them is not is a defect unless the
# site asked for it, and a site that asked is not what CI builds.
MAJOR_BOTS = ["gptbot", "claudebot", "google-extended", "perplexitybot"]

LD_RE = re.compile(
    r"""<script[^>]*type=["']?application/ld\+json["']?[^>]*>(.*?)</script>""",
    re.S | re.I)


def parse_robots(text):
    """robots.txt as {agent: {"allow": [...], "disallow": [...]}}.

    Consecutive User-agent lines share the rules that follow them, which is the
    standard's own grouping and the shape the theme emits. A blank line ends a
    group; a comment does not.
    """
    groups = {}
    current = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            current = []
            continue
        if line.startswith("#"):
            continue
        m = re.match(r"^user-agent:\s*(.+)$", line, re.I)
        if m:
            agent = m.group(1).strip().lower()
            current.append(agent)
            groups.setdefault(agent, {"allow": [], "disallow": []})
            continue
        m = re.match(r"^(allow|disallow):\s*(.*)$", line, re.I)
        if m and current:
            for agent in current:
                groups[agent][m.group(1).lower()].append(m.group(2).strip())
    return groups


def allowed(groups, agent):
    """Whether one agent may fetch /, by the rules in this file.

    Its own group wins outright when it has one -- a bot never reads the `*`
    group once it has matched its own name, which is the whole reason the theme
    repeats the site's disallow list into every group it writes.
    """
    own = groups.get(agent.lower())
    if own is not None:
        return not ("/" in own["disallow"] and "/" not in own["allow"])
    star = groups.get("*")
    if star is None:
        return True
    return "/" not in star["disallow"] or "/" in star["allow"]


def check_robots(public, indexable):
    problems = []
    path = public / "robots.txt"
    if not path.is_file():
        return ["robots.txt: not in the build -- the site needs enableRobotsTXT = true"]
    text = path.read_text()

    sitemaps = re.findall(r"^\s*sitemap:\s*(\S+)\s*$", text, re.I | re.M)
    if len(sitemaps) != 1:
        problems.append("robots.txt: expected exactly 1 Sitemap line, found %d"
                        % len(sitemaps))
    for url in sitemaps:
        name = url.rstrip("/").rsplit("/", 1)[-1]
        if not (public / name).is_file():
            problems.append("robots.txt: Sitemap names %s, which the build did not "
                            "publish" % url)

    groups = parse_robots(text)
    if not groups:
        problems.append("robots.txt: no User-agent group parsed out of it at all")
    for agent, rules in groups.items():
        if not rules["allow"] and not rules["disallow"]:
            problems.append("robots.txt: the %s group carries no rule, so nothing "
                            "in it applies" % agent)

    if indexable:
        for bot in MAJOR_BOTS:
            if not allowed(groups, bot):
                problems.append("robots.txt: %s is blocked" % bot)
        star = groups.get("*", {"disallow": [], "allow": []})
        if "/" in star["disallow"]:
            problems.append("robots.txt: `User-agent: *` carries `Disallow: /` -- "
                            "this build switches the whole site off")
    else:
        if allowed(groups, "gptbot"):
            problems.append("robots.txt: a build that is not for indexing still "
                            "invites crawlers")
    return problems


def json_ld(html):
    """Every ld+json block on a page, parsed. Raises on the first bad one."""
    out = []
    for i, block in enumerate(LD_RE.findall(html)):
        try:
            out.append(json.loads(block))
        except json.JSONDecodeError as exc:
            raise ValueError("block %d is not valid JSON: %s" % (i + 1, exc))
    return out


def check_page(rel, html):
    problems = []
    try:
        nodes = json_ld(html)
    except ValueError as exc:
        return ["%s: %s" % (rel, exc)]

    if not nodes:
        return ["%s: no JSON-LD at all" % rel]

    types = [n.get("@type") for n in nodes]
    defined = {n["@id"] for n in nodes if "@id" in n}

    for node in nodes:
        if node.get("@context") != "https://schema.org":
            problems.append("%s: a %s node with no @context" % (rel, node.get("@type")))

    if not ({"Person", "Organization"} & set(types)):
        problems.append("%s: no Person or Organization -- every other node "
                        "references it" % rel)
    if "WebSite" not in types:
        problems.append("%s: no WebSite node" % rel)

    # A reference to an @id nothing on the page defines is a dangling edge: the
    # consumer resolves it to nothing and the author or publisher disappears.
    for node in nodes:
        for field in ("author", "publisher", "isPartOf"):
            ref = node.get(field)
            if isinstance(ref, dict) and set(ref) == {"@id"} and ref["@id"] not in defined:
                problems.append("%s: %s.%s points at %s, which no node here defines"
                                % (rel, node.get("@type"), field, ref["@id"]))

    for node in nodes:
        if node.get("@type") == "BlogPosting":
            for field in ("headline", "datePublished", "author", "inLanguage",
                          "mainEntityOfPage", "wordCount"):
                if field not in node:
                    problems.append("%s: BlogPosting has no %s" % (rel, field))
            if len(node.get("headline", "")) > 110:
                problems.append("%s: headline is %d characters; Google drops it over "
                                "110" % (rel, len(node["headline"])))
        if node.get("@type") == "BreadcrumbList":
            crumbs = node.get("itemListElement", [])
            positions = [c.get("position") for c in crumbs]
            if positions != list(range(1, len(crumbs) + 1)):
                problems.append("%s: breadcrumb positions are %s, not 1..%d"
                                % (rel, positions, len(crumbs)))
            if crumbs and "item" in crumbs[-1]:
                problems.append("%s: the last breadcrumb links to itself" % rel)
            for crumb in crumbs[:-1]:
                if not crumb.get("item"):
                    problems.append("%s: a breadcrumb before the last has no item"
                                    % rel)
    return problems


def check(public_dir, expect_robots=True, indexable=True):
    public = pathlib.Path(public_dir)
    problems = []
    if expect_robots:
        problems += check_robots(public, indexable)

    pages = sorted(public.rglob("*.html"))
    if not pages:
        return ["%s: no HTML in it -- nothing was checked" % public_dir]

    home = public / "index.html"
    if home.is_file():
        problems += check_page("/", home.read_text())

    posts = 0
    for path in pages:
        rel = "/" + str(path.relative_to(public))
        html = path.read_text()
        if "BlogPosting" in html:
            posts += 1
            problems += check_page(rel, html)
    if posts == 0:
        problems.append("%s: not one page carried a BlogPosting, so the post half "
                        "of this check verified nothing" % public_dir)
    return problems


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if not args:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    problems = check(args[0],
                     expect_robots="--no-robots" not in flags,
                     indexable="--not-indexable" not in flags)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        print("\n%d problem(s) in the AEO output." % len(problems), file=sys.stderr)
        return 1
    print("%s: robots.txt and the JSON-LD graph check out" % args[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
