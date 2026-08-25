"""Tests for check_aeo.py.

The robots.txt parser gets most of them, because it is the part with rules of
its own rather than a field list: consecutive User-agent lines share a group, a
blank line ends one, a comment does not, and a bot that has its own group never
reads the `*` group. That last one is the reason the theme repeats its disallow
list into every group it writes, so it is worth pinning rather than assuming.

The page checks are covered against hand-built HTML rather than a build, so a
failure here is a defect in the checker and never in Hugo.
"""

import pathlib
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_aeo as aeo  # noqa: E402


def page(*blocks):
    scripts = "".join(
        '<script type="application/ld+json">%s</script>' % b for b in blocks)
    return "<html><head>%s</head><body></body></html>" % scripts


PUBLISHER = ('{"@context":"https://schema.org","@type":"Person",'
             '"@id":"https://x/#person","name":"A"}')
WEBSITE = ('{"@context":"https://schema.org","@type":"WebSite",'
           '"@id":"https://x/#website","name":"A",'
           '"publisher":{"@id":"https://x/#person"}}')
POST = ('{"@context":"https://schema.org","@type":"BlogPosting",'
        '"headline":"H","datePublished":"2026-01-01T00:00:00Z",'
        '"author":{"@id":"https://x/#person"},"inLanguage":"en",'
        '"mainEntityOfPage":"https://x/p/","wordCount":10}')

# A section index, a tag list, a term page: what the theme emits for the pages
# whose content is the set of pages they link to.
COLLECTION = ('{"@context":"https://schema.org","@type":"CollectionPage",'
              '"@id":"https://x/blogs/#page","url":"https://x/blogs/",'
              '"name":"Blog","isPartOf":{"@id":"https://x/#website"},'
              '"inLanguage":"en","breadcrumb":{"@id":"https://x/blogs/#breadcrumb"}}')
COLLECTION_CRUMBS = (
    '{"@context":"https://schema.org","@type":"BreadcrumbList",'
    '"@id":"https://x/blogs/#breadcrumb","itemListElement":['
    '{"@type":"ListItem","position":1,"name":"Home","item":"https://x/"},'
    '{"@type":"ListItem","position":2,"name":"Blog"}]}')
CRUMBS = ('{"@context":"https://schema.org","@type":"BreadcrumbList",'
          '"itemListElement":['
          '{"@type":"ListItem","position":1,"name":"Home","item":"https://x/"},'
          '{"@type":"ListItem","position":2,"name":"P"}]}')


class RobotsParsing(unittest.TestCase):
    def test_consecutive_agents_share_the_rules_below_them(self):
        g = aeo.parse_robots("User-agent: A\nUser-agent: B\nAllow: /\n")
        self.assertEqual(g["a"]["allow"], ["/"])
        self.assertEqual(g["b"]["allow"], ["/"])

    def test_a_blank_line_ends_a_group(self):
        g = aeo.parse_robots("User-agent: A\nAllow: /\n\nUser-agent: B\nDisallow: /\n")
        self.assertEqual(g["a"]["disallow"], [])
        self.assertEqual(g["b"]["disallow"], ["/"])

    def test_a_comment_does_not_end_a_group(self):
        g = aeo.parse_robots("User-agent: A\n# still A\nAllow: /\n")
        self.assertEqual(g["a"]["allow"], ["/"])

    def test_an_own_group_wins_over_the_wildcard(self):
        text = "User-agent: *\nDisallow: /\n\nUser-agent: Good\nAllow: /\n"
        g = aeo.parse_robots(text)
        self.assertTrue(aeo.allowed(g, "Good"))
        self.assertFalse(aeo.allowed(g, "Other"))

    def test_the_wildcard_applies_to_a_bot_with_no_group(self):
        g = aeo.parse_robots("User-agent: *\nAllow: /\n")
        self.assertTrue(aeo.allowed(g, "Anything"))

    def test_agent_matching_ignores_case(self):
        g = aeo.parse_robots("User-agent: GPTBot\nDisallow: /\n")
        self.assertFalse(aeo.allowed(g, "gptbot"))


class RobotsChecks(unittest.TestCase):
    def run_on(self, robots, indexable=True, training_blocked=False):
        with tempfile.TemporaryDirectory() as d:
            pub = pathlib.Path(d)
            (pub / "sitemap.xml").write_text("<urlset/>")
            (pub / "robots.txt").write_text(robots)
            return aeo.check_robots(pub, indexable, training_blocked)

    GOOD = ("User-agent: *\nAllow: /\n\n"
            "User-agent: GPTBot\nUser-agent: ClaudeBot\n"
            "User-agent: Google-Extended\nUser-agent: PerplexityBot\nAllow: /\n\n"
            "Sitemap: https://x/sitemap.xml\n")

    def test_a_good_file_passes(self):
        self.assertEqual(self.run_on(self.GOOD), [])

    def test_a_sitemap_that_is_not_in_the_build(self):
        bad = self.GOOD.replace("sitemap.xml", "nope.xml")
        self.assertTrue(any("did not publish" in p for p in self.run_on(bad)))

    def test_no_sitemap_line_at_all(self):
        bad = self.GOOD.replace("Sitemap: https://x/sitemap.xml\n", "")
        self.assertTrue(any("Sitemap line" in p for p in self.run_on(bad)))

    def test_a_group_with_no_rule(self):
        bad = self.GOOD + "\nUser-agent: Lonely\n"
        self.assertTrue(any("carries no rule" in p for p in self.run_on(bad)))

    def test_a_blocked_major_bot(self):
        bad = self.GOOD.replace("User-agent: PerplexityBot\nAllow: /",
                                "User-agent: PerplexityBot\nDisallow: /")
        self.assertTrue(any("perplexitybot is blocked" in p for p in self.run_on(bad)))

    def test_a_blanket_disallow_on_an_indexable_build(self):
        bad = "User-agent: *\nDisallow: /\n\nSitemap: https://x/sitemap.xml\n"
        self.assertTrue(any("switches the whole site off" in p
                            for p in self.run_on(bad)))

    def test_a_non_indexable_build_must_actually_block(self):
        # The inverse net: a preview that renders the permissive file is the
        # defect this direction is watching for.
        self.assertTrue(any("still invites crawlers" in p
                            for p in self.run_on(self.GOOD, indexable=False)))

    def test_a_preview_is_allowed_to_have_no_sitemap(self):
        # The template drops the Sitemap line on a build that is not for
        # indexing, which is correct -- and this check used to run regardless,
        # so the script's only preview mode rejected the theme's own output.
        preview = "User-agent: *\nDisallow: /\n"
        self.assertEqual(self.run_on(preview, indexable=False), [])

    def test_a_site_that_blocks_training_is_not_three_failures(self):
        # Three of the four MAJOR_BOTS are training crawlers, so a site using
        # [params.aeo] allowTraining = false failed this check for doing exactly
        # what the switch is for.
        blocked = self.GOOD.replace(
            "User-agent: GPTBot\nUser-agent: ClaudeBot\n"
            "User-agent: Google-Extended\nUser-agent: PerplexityBot\nAllow: /",
            "User-agent: PerplexityBot\nAllow: /\n\n"
            "User-agent: GPTBot\nUser-agent: ClaudeBot\n"
            "User-agent: Google-Extended\nDisallow: /")
        self.assertTrue(any("is blocked" in p for p in self.run_on(blocked)))
        self.assertEqual(self.run_on(blocked, training_blocked=True), [])

    def test_training_blocked_is_an_assertion_not_a_mute(self):
        # The inverse: claiming training is blocked on a build that allows it.
        problems = self.run_on(self.GOOD, training_blocked=True)
        self.assertTrue(any("still allowed" in p for p in problems), problems)

    def test_a_preview_that_still_points_at_a_sitemap_is_a_problem(self):
        preview = "User-agent: *\nDisallow: /\n\nSitemap: https://x/sitemap.xml\n"
        self.assertTrue(any("still points a Sitemap" in p
                            for p in self.run_on(preview, indexable=False)))


class PageChecks(unittest.TestCase):
    def test_a_complete_post_page_passes(self):
        self.assertEqual(aeo.check_page("/p/", page(PUBLISHER, WEBSITE, POST, CRUMBS)), [])

    def test_a_page_with_no_json_ld(self):
        self.assertTrue(aeo.check_page("/p/", "<html></html>"))

    def test_a_dangling_id_reference(self):
        html = page(PUBLISHER.replace("#person", "#someone-else"), WEBSITE)
        self.assertTrue(any("no node here defines" in p
                            for p in aeo.check_page("/", html)))

    def test_a_missing_blogposting_field(self):
        html = page(PUBLISHER, WEBSITE, POST.replace(',"wordCount":10', ""))
        self.assertTrue(any("no wordCount" in p for p in aeo.check_page("/p/", html)))

    def test_a_headline_over_the_google_cap(self):
        html = page(PUBLISHER, WEBSITE, POST.replace('"headline":"H"',
                                                     '"headline":"%s"' % ("x" * 120)))
        self.assertTrue(any("110" in p for p in aeo.check_page("/p/", html)))

    def test_a_breadcrumb_with_a_gap(self):
        html = page(PUBLISHER, WEBSITE, CRUMBS.replace('"position":2', '"position":5'))
        self.assertTrue(any("not 1..2" in p for p in aeo.check_page("/p/", html)))

    def test_a_last_crumb_that_links_to_itself(self):
        html = page(PUBLISHER, WEBSITE,
                    CRUMBS.replace('"position":2,"name":"P"',
                                   '"position":2,"name":"P","item":"https://x/p/"'))
        self.assertTrue(any("links to itself" in p for p in aeo.check_page("/p/", html)))

    def test_unquoted_type_is_still_found(self):
        # hugo --minify drops the quotes, and a checker that requires them reads
        # a perfectly good page as having no structured data at all. That is the
        # bug this theme works around in aeo.js; it must not repeat it here.
        html = page(PUBLISHER, WEBSITE).replace('type="application/ld+json"',
                                                "type=application/ld+json")
        self.assertEqual(aeo.check_page("/", html), [])

    def test_a_block_that_is_not_valid_json(self):
        html = page(PUBLISHER, WEBSITE, "{not json}")
        self.assertTrue(any("not valid JSON" in p for p in aeo.check_page("/", html)))


LLMS = """# Site

> What it is

- Language: en
- Home: https://x/t/
- Full text of every post, in one file: https://x/t/llms-full.txt

## Blog

- [One](https://x/t/blogs/one/index.md): first
- [Two](https://x/t/blogs/two/index.md): second
"""


def llms_site(d, llms=LLMS, lang_dir="", full=True, twins=("one", "two")):
    """A published tree just complete enough for the llms checks to run."""
    root = pathlib.Path(d)
    here = root / lang_dir if lang_dir else root
    here.mkdir(parents=True, exist_ok=True)
    (here / "llms.txt").write_text(llms)
    if full:
        (here / "llms-full.txt").write_text("# Site\n")
    for name in twins:
        post = here / "blogs" / name
        post.mkdir(parents=True, exist_ok=True)
        (post / "index.html").write_text("<html></html>")
        (post / "index.md").write_text(
            "# %s\n\n- URL: https://x/t/%sblogs/%s/\n" %
            (name, (lang_dir + "/") if lang_dir else "", name))
    return root


class LlmsChecks(unittest.TestCase):
    def test_a_complete_index_passes(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(aeo.check_llms(llms_site(d)), [])

    def test_a_link_the_build_did_not_publish(self):
        with tempfile.TemporaryDirectory() as d:
            root = llms_site(d, twins=("one",))
            self.assertTrue(any("did not publish" in p
                                for p in aeo.check_llms(root)))

    def test_a_missing_llms_full(self):
        with tempfile.TemporaryDirectory() as d:
            root = llms_site(d, full=False)
            self.assertTrue(any("no llms-full.txt" in p
                                for p in aeo.check_llms(root)))

    def test_no_h1(self):
        with tempfile.TemporaryDirectory() as d:
            root = llms_site(d, llms=LLMS.replace("# Site", "Site", 1))
            self.assertTrue(any("H1" in p for p in aeo.check_llms(root)))

    def test_no_h2_section(self):
        with tempfile.TemporaryDirectory() as d:
            root = llms_site(d, llms=LLMS.replace("## Blog\n", ""))
            self.assertTrue(any("H2 section" in p for p in aeo.check_llms(root)))

    def test_a_blank_line_splitting_the_list(self):
        with tempfile.TemporaryDirectory() as d:
            broken = LLMS.replace("- [One](https://x/t/blogs/one/index.md): first\n",
                                  "- [One](https://x/t/blogs/one/index.md): first\n\n")
            root = llms_site(d, llms=broken)
            self.assertTrue(any("blank line splits" in p
                                for p in aeo.check_llms(root)))

    def test_a_second_language_resolves_against_the_site_root(self):
        # /pt/llms.txt names /t/pt/ as its home while its links are rooted at
        # /t/. Subtracting the file's own directory is what makes them resolve —
        # without it every link in the second language reads as broken.
        with tempfile.TemporaryDirectory() as d:
            pt = LLMS.replace("- Home: https://x/t/", "- Home: https://x/t/pt/") \
                     .replace("https://x/t/blogs/", "https://x/t/pt/blogs/") \
                     .replace("https://x/t/llms-full.txt", "https://x/t/pt/llms-full.txt")
            root = llms_site(d, llms=pt, lang_dir="pt")
            self.assertEqual(aeo.check_llms(root), [])

    def test_a_percent_encoded_link(self):
        # Hugo publishes tags/migração/ and links tags/migra%C3%A7%C3%A3o/.
        with tempfile.TemporaryDirectory() as d:
            root = llms_site(d)
            tag = root / "tags" / "migração"
            tag.mkdir(parents=True)
            (tag / "index.html").write_text("<html></html>")
            extra = LLMS + "- [migração](https://x/t/tags/migra%C3%A7%C3%A3o/): 1 post\n"
            (root / "llms.txt").write_text(extra)
            self.assertEqual(aeo.check_llms(root), [])

    def test_a_build_with_no_llms_at_all(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(aeo.check_llms(pathlib.Path(d)))


class MarkdownChecks(unittest.TestCase):
    def test_complete_twins_pass(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(aeo.check_markdown(llms_site(d)), [])

    def test_a_twin_naming_a_different_page(self):
        with tempfile.TemporaryDirectory() as d:
            root = llms_site(d)
            (root / "blogs" / "one" / "index.md").write_text(
                "# One\n\n- URL: https://x/t/blogs/elsewhere/\n")
            self.assertTrue(any("different page" in p
                                for p in aeo.check_markdown(root)))

    def test_a_twin_with_no_url(self):
        with tempfile.TemporaryDirectory() as d:
            root = llms_site(d)
            (root / "blogs" / "one" / "index.md").write_text("# One\n\nbody\n")
            self.assertTrue(any("no canonical URL" in p
                                for p in aeo.check_markdown(root)))

    def test_a_twin_with_no_html_beside_it(self):
        with tempfile.TemporaryDirectory() as d:
            root = llms_site(d)
            (root / "blogs" / "one" / "index.html").unlink()
            self.assertTrue(any("no index.html" in p
                                for p in aeo.check_markdown(root)))

    def test_a_build_with_no_twins_at_all(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(aeo.check_markdown(pathlib.Path(d)))

class HeadlineChecks(unittest.TestCase):
    def test_a_headline_that_is_not_the_name_it_came_from(self):
        # truncate escapes a plain string, so headline used to arrive with HTML
        # entities in it while name -- the same title, same node -- did not.
        bad = POST.replace('"headline":"H"',
                           '"headline":"Vue &amp; Vitest"') \
                  .replace('"wordCount":10', '"wordCount":10,"name":"Vue & Vitest"')
        problems = aeo.check_page("/p/", page(PUBLISHER, WEBSITE, bad))
        self.assertTrue(any("is not the start of name" in p for p in problems),
                        problems)

    def test_a_truncated_headline_still_matches_its_name(self):
        ok = POST.replace('"headline":"H"', '"headline":"A long title th…"') \
                 .replace('"wordCount":10',
                          '"wordCount":10,"name":"A long title that kept going"')
        self.assertEqual(aeo.check_page("/p/", page(PUBLISHER, WEBSITE, ok)), [])


class CollectionChecks(unittest.TestCase):
    def test_a_list_page_passes(self):
        self.assertEqual(
            aeo.check_page("/blogs/", page(PUBLISHER, WEBSITE, COLLECTION,
                                           COLLECTION_CRUMBS)), [])

    def test_a_breadcrumb_leading_to_nothing(self):
        # What a list page used to emit: a trail to a page the graph says
        # nothing else about. It is the dangling shape one level up, and the
        # @id check cannot see it because a BreadcrumbList names no @id.
        problems = aeo.check_page("/blogs/", page(PUBLISHER, WEBSITE,
                                                  COLLECTION_CRUMBS))
        self.assertTrue(any("lead to" in p for p in problems), problems)

    def test_a_phantom_mainentityofpage_is_caught(self):
        # `dict "@type" "WebPage" "@id" .Permalink` declared a second node for
        # the page -- no url, no name, at an @id nothing else defines -- beside
        # the BlogPosting that is the thing being described.
        bad = POST.replace('"mainEntityOfPage":"https://x/p/"',
                           '"mainEntityOfPage":{"@id":"https://x/p/"}')
        problems = aeo.check_page("/p/", page(PUBLISHER, WEBSITE, bad))
        self.assertTrue(any("mainEntityOfPage" in p and "no node here defines" in p
                            for p in problems), problems)


class Wiring(unittest.TestCase):
    def test_an_empty_directory_is_a_failure_not_a_pass(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(aeo.check(d, expect_robots=False))

    def test_a_site_with_no_post_is_a_failure(self):
        # Otherwise the BlogPosting half of the suite passes by never running.
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "index.html").write_text(page(PUBLISHER, WEBSITE))
            self.assertTrue(any("not one page carried a BlogPosting" in p
                                for p in aeo.check(d, expect_robots=False)))

    def test_a_page_that_is_not_a_post_is_checked_too(self):
        # The gate used to be `if "BlogPosting" in html`, so the lists, the
        # taxonomies and the whole WebPage branch were never looked at: a
        # /blogs/index.html with a corrupted graph came back clean.
        with tempfile.TemporaryDirectory() as d:
            pub = pathlib.Path(d)
            (pub / "index.html").write_text(page(PUBLISHER, WEBSITE))
            (pub / "p").mkdir()
            (pub / "p" / "index.html").write_text(page(PUBLISHER, WEBSITE, POST))
            (pub / "blogs").mkdir()
            (pub / "blogs" / "index.html").write_text(
                '<html><head><script type="application/ld+json">{BROKEN'
                "</script></head></html>")
            problems = aeo.check(d, expect_robots=False)
            self.assertTrue(any("/blogs/index.html" in p for p in problems),
                            problems)

    def test_a_redirect_stub_is_not_a_page_that_lost_its_graph(self):
        # Hugo writes one per alias, and for the root index.html of a site with
        # defaultContentLanguageInSubdir. Reading one as a page missing its
        # JSON-LD failed a build that was correct.
        with tempfile.TemporaryDirectory() as d:
            pub = pathlib.Path(d)
            (pub / "index.html").write_text(
                '<html><head><meta http-equiv="refresh" content="0; '
                'url=https://x/en/"></head></html>')
            (pub / "en").mkdir()
            (pub / "en" / "index.html").write_text(page(PUBLISHER, WEBSITE, POST))
            self.assertEqual(aeo.check(d, expect_robots=False, expect_llms=False,
                                       expect_markdown=False), [])

    def test_an_unknown_flag_is_rejected(self):
        # --not-indexible used to be accepted in silence, and the mode the
        # caller asked for simply did not happen.
        self.assertEqual(aeo.main(["check_aeo.py", "somewhere", "--not-indexible"]), 2)

    def test_main_returns_zero_on_a_clean_tree(self):
        # The green path through main() -- the one that builds the summary line
        # -- had no test at all, and a merge renamed the dict under it. Every
        # other test calls check() directly, which walks straight past it.
        with tempfile.TemporaryDirectory() as d:
            pub = pathlib.Path(d)
            (pub / "index.html").write_text(page(PUBLISHER, WEBSITE))
            (pub / "p").mkdir()
            (pub / "p" / "index.html").write_text(page(PUBLISHER, WEBSITE, POST))
            self.assertEqual(
                aeo.main(["check_aeo.py", d, "--no-robots", "--no-llms",
                          "--no-markdown"]), 0)

    def test_every_flag_the_usage_line_documents_is_accepted(self):
        # The guard above and the flags main() reads are one mapping for a
        # reason: two hand-written lists disagree the moment a flag is added,
        # and the failure is a real flag refused as unknown.
        documented = set(re.findall(r"--[a-z-]+", " ".join(aeo.usage())))
        self.assertEqual(documented, set(aeo.FLAGS), "usage line and FLAGS differ")
        with tempfile.TemporaryDirectory() as d:
            for flag in sorted(aeo.FLAGS):
                with self.subTest(flag=flag):
                    self.assertNotEqual(
                        aeo.main(["check_aeo.py", d, flag]), 2,
                        "%s is documented but rejected as unknown" % flag)


if __name__ == "__main__":
    unittest.main()
