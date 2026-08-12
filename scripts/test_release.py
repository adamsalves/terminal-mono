#!/usr/bin/env python3
"""Tests for the release tooling.

    python3 -m unittest discover -s scripts -v

Covers the pure logic — changelog promotion, note extraction, tag ordering,
token scoping, credential redaction and the CI gate — against the repository's
real CHANGELOG.md wherever possible. Nothing here touches the network or
mutates the repo.
"""

import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(filename, name):
    """Import a script by path — release-notes.py is not a valid module name."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load("release.py", "release_script")
notes = load("release-notes.py", "release_notes_script")

with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as handle:
    REAL_CHANGELOG = handle.read()

# A miniature changelog with the same shape as the real one: an [Unreleased]
# section, two releases, and the link-reference block that closes the file.
SAMPLE = """\
# Changelog

## [Unreleased]

### Added
- Something new.

## [0.2.0] — 2026-01-02

### Fixed
- An old bug.

## [0.1.0] — 2026-01-01

### Added
- The first release.

[Unreleased]: https://github.com/o/r/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/o/r/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/o/r/releases/tag/v0.1.0
"""


def seeded(changelog_text):
    """The changelog with an [Unreleased] entry, adding one only if it is bare.

    Lets a test exercise promotion against the real file without caring whether
    a release has just emptied that section.
    """
    body = re.search(
        r"^## \[Unreleased\][ \t]*\n(.*?)(?=^## \[|^\[[^\]]+\]:\s|\Z)",
        changelog_text, re.M | re.S,
    )
    if body and body.group(1).strip():
        return changelog_text
    return changelog_text.replace(
        "## [Unreleased]\n", "## [Unreleased]\n\n### Added\n- Seeded by the tests.\n", 1
    )


class PromoteChangelog(unittest.TestCase):
    def promote(self, text=SAMPLE, version="0.3.0", today="2026-02-03"):
        return release.promote_changelog(text, version, today)

    def test_spacing_matches_the_existing_sections(self):
        """One blank line on each side of the new heading — like every other one."""
        out, _ = self.promote()
        self.assertIn("## [Unreleased]\n\n## [0.3.0] — 2026-02-03\n\n### Added\n", out)
        self.assertNotIn("\n\n\n", out)

    def test_promoting_is_idempotent_in_shape(self):
        """Promoting twice in a row must not accrete blank lines."""
        once, _ = self.promote()
        twice, _ = release.promote_changelog(
            once.replace("## [Unreleased]\n\n", "## [Unreleased]\n\n### Added\n- More.\n\n", 1),
            "0.4.0", "2026-02-04",
        )
        self.assertNotIn("\n\n\n", twice)

    def test_chains_the_compare_links(self):
        out, previous = self.promote()
        self.assertEqual(previous, "v0.2.0")
        self.assertIn("[Unreleased]: https://github.com/o/r/compare/v0.3.0...HEAD\n", out)
        self.assertIn("[0.3.0]: https://github.com/o/r/compare/v0.2.0...v0.3.0\n", out)
        self.assertIn("[0.2.0]: https://github.com/o/r/compare/v0.1.0...v0.2.0\n", out)

    def test_keeps_the_unreleased_entries_under_the_new_version(self):
        out, _ = self.promote()
        body = out.split("## [0.3.0]")[1].split("## [0.2.0]")[0]
        self.assertIn("- Something new.", body)
        unreleased = out.split("## [Unreleased]")[1].split("## [0.3.0]")[0]
        self.assertEqual(unreleased.strip(), "")

    def test_refuses_an_empty_unreleased_section(self):
        empty = SAMPLE.replace("### Added\n- Something new.\n\n", "", 1)
        with self.assertRaises(SystemExit) as caught:
            self.promote(empty)
        self.assertIn("nothing to release", str(caught.exception))

    def test_refuses_a_duplicate_version(self):
        with self.assertRaises(SystemExit) as caught:
            self.promote(version="0.2.0")
        self.assertIn("already has a '## [0.2.0]' section", str(caught.exception))

    def test_refuses_a_changelog_with_no_unreleased_heading(self):
        with self.assertRaises(SystemExit) as caught:
            self.promote(SAMPLE.replace("## [Unreleased]\n", "", 1))
        self.assertIn("no '## [Unreleased]' heading", str(caught.exception))

    def test_refuses_a_changelog_with_no_unreleased_link(self):
        stripped = SAMPLE.replace(
            "[Unreleased]: https://github.com/o/r/compare/v0.2.0...HEAD\n", "", 1
        )
        with self.assertRaises(SystemExit) as caught:
            self.promote(stripped)
        self.assertIn("compare/vX...HEAD", str(caught.exception))

    def test_detects_entries_when_no_release_section_follows(self):
        """A changelog whose only section is [Unreleased] still has entries.

        The body scan stops at the link block, not just at the next heading.
        """
        first = "# Changelog\n\n## [Unreleased]\n\n### Added\n- The first thing.\n\n" \
                "[Unreleased]: https://github.com/o/r/compare/v0.0.1...HEAD\n"
        out, previous = release.promote_changelog(first, "0.1.0", "2026-02-03")
        self.assertEqual(previous, "v0.0.1")
        self.assertIn("## [0.1.0] — 2026-02-03", out)

    def test_runs_against_the_real_changelog(self):
        """The real file's shape, whatever state the release cycle left it in.

        [Unreleased] is empty by design straight after a promotion — which is
        precisely when this runs, since ci.yml tests the release PR — so seed
        it rather than assert a state the release flow deliberately removes.
        """
        out, previous = release.promote_changelog(
            seeded(REAL_CHANGELOG), "9.9.9", "2026-02-03"
        )
        self.assertIn("## [Unreleased]\n\n## [9.9.9] — 2026-02-03\n\n###", out)
        self.assertIn(f"[9.9.9]: https://github.com/adamsalves/terminal-mono/compare/"
                      f"{previous}...v9.9.9\n", out)

    def test_refuses_the_real_changelog_right_after_a_release(self):
        """The state that broke this suite on the v0.2.3 release PR."""
        promoted, _ = release.promote_changelog(
            seeded(REAL_CHANGELOG), "9.9.9", "2026-02-03"
        )
        with self.assertRaises(SystemExit) as caught:
            release.promote_changelog(promoted, "9.9.10", "2026-02-04")
        self.assertIn("nothing to release", str(caught.exception))


class NotesFor(unittest.TestCase):
    def test_extracts_a_middle_section(self):
        body = notes.notes_for("0.2.0", SAMPLE, tags=[])
        self.assertEqual(body, "### Fixed\n- An old bug.")

    def test_extracts_the_last_section_in_the_file(self):
        """The oldest release has no heading after it, only the link block.

        Backfilling a Release for it is one of the reasons this script exists.
        """
        body = notes.notes_for("0.1.0", SAMPLE, tags=[])
        self.assertEqual(body, "### Added\n- The first release.")

    def test_never_swallows_the_link_reference_block(self):
        body = notes.notes_for("0.1.0", SAMPLE, tags=[])
        self.assertNotIn("[Unreleased]:", body)
        self.assertNotIn("releases/tag", body)

    def test_appends_the_compare_link(self):
        body = notes.notes_for("0.2.0", SAMPLE, tags=["v0.1.0", "v0.2.0"])
        self.assertTrue(body.endswith("/compare/v0.1.0...v0.2.0"), body)

    def test_reports_the_sections_that_do_exist_when_one_is_missing(self):
        with self.assertRaises(SystemExit) as caught:
            notes.notes_for("7.7.7", SAMPLE, tags=[])
        message = str(caught.exception)
        self.assertIn("no '## [7.7.7]' section", message)
        self.assertIn("Unreleased, 0.2.0, 0.1.0", message)

    def test_rejects_an_empty_section(self):
        hollow = SAMPLE.replace("### Fixed\n- An old bug.\n", "")
        with self.assertRaises(SystemExit) as caught:
            notes.notes_for("0.2.0", hollow, tags=[])
        self.assertIn("is empty", str(caught.exception))

    def test_every_real_changelog_section_is_extractable(self):
        """Including the oldest — the case that used to fail."""
        versions = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", REAL_CHANGELOG, re.M)
        self.assertGreater(len(versions), 1)
        for version in versions:
            with self.subTest(version=version):
                body = notes.notes_for(version, REAL_CHANGELOG, tags=[])
                self.assertTrue(body.strip())
                self.assertNotIn("[Unreleased]:", body)


class PreviousTag(unittest.TestCase):
    TAGS = ["v0.1.0", "v0.2.0", "v0.2.1", "v0.2.2", "v0.3.0"]

    def test_picks_the_immediately_lower_version(self):
        self.assertEqual(notes.previous_tag("v0.2.2", self.TAGS), "v0.2.1")

    def test_orders_numerically_not_lexically(self):
        self.assertEqual(notes.previous_tag("v0.11.0", ["v0.9.0", "v0.10.0"]), "v0.10.0")

    def test_ignores_higher_versions(self):
        """A late patch must not compare against a newer minor — that reverses
        the range, which is what the sidebar renders as an empty diff."""
        self.assertEqual(notes.previous_tag("v0.2.3", self.TAGS), "v0.2.2")

    def test_returns_none_for_the_first_release(self):
        self.assertIsNone(notes.previous_tag("v0.1.0", self.TAGS))

    def test_skips_tags_that_are_not_semver(self):
        self.assertEqual(notes.previous_tag("v0.2.0", ["v0.1.0", "nightly", "v1"]), "v0.1.0")


class TokenScoping(unittest.TestCase):
    MULTI_HOST = """\
ghe.example.com:
    oauth_token: ENTERPRISE_TOKEN
    user: someone
github.com:
    oauth_token: DOTCOM_TOKEN
    user: someone
"""

    def test_reads_the_github_com_token_not_the_first_one(self):
        """An enterprise token sent to api.github.com is a credential leak."""
        self.assertEqual(
            release.github_com_token(self.MULTI_HOST), "DOTCOM_TOKEN"
        )

    def test_reads_a_single_host_file(self):
        single = "github.com:\n    oauth_token: ONLY\n    user: someone\n"
        self.assertEqual(release.github_com_token(single), "ONLY")

    def test_handles_the_nested_users_block_gh_writes(self):
        nested = (
            "github.com:\n"
            "    users:\n"
            "        someone:\n"
            "            oauth_token: NESTED\n"
            "    git_protocol: https\n"
            "    oauth_token: NESTED\n"
        )
        self.assertEqual(release.github_com_token(nested), "NESTED")

    def test_returns_none_when_github_com_is_absent(self):
        only_ghe = "ghe.example.com:\n    oauth_token: ENTERPRISE_TOKEN\n"
        self.assertIsNone(release.github_com_token(only_ghe))


class SlugFromURL(unittest.TestCase):
    def test_parses_every_remote_form_git_produces(self):
        for url in (
            "https://github.com/adamsalves/terminal-mono.git",
            "https://github.com/adamsalves/terminal-mono",
            "git@github.com:adamsalves/terminal-mono.git",
            "git@github.com:adamsalves/terminal-mono",
            "ssh://git@github.com/adamsalves/terminal-mono.git",
            "https://x-access-token:ghp_SECRET@github.com/adamsalves/terminal-mono.git",
            "https://github.com/adamsalves/terminal-mono/",
        ):
            with self.subTest(url=url):
                self.assertEqual(release.slug_from_url(url), "adamsalves/terminal-mono")

    def test_rejects_a_non_github_url(self):
        self.assertIsNone(release.slug_from_url("https://gitlab.com/o/r.git"))


class Redaction(unittest.TestCase):
    def test_blanks_a_token_embedded_in_a_remote_url(self):
        url = "https://x-access-token:ghp_SECRET@github.com/o/r.git"
        self.assertEqual(release.redact(url), "https://***@github.com/o/r.git")
        self.assertNotIn("ghp_SECRET", release.redact(url))

    def test_blanks_a_token_inside_a_longer_message(self):
        message = "git push https://user:ghp_SECRET@github.com/o/r.git main\nerror: denied"
        self.assertNotIn("ghp_SECRET", release.redact(message))
        self.assertIn("error: denied", release.redact(message))

    def test_leaves_a_clean_url_alone(self):
        url = "https://github.com/o/r.git"
        self.assertEqual(release.redact(url), url)

    def test_leaves_ssh_remotes_alone(self):
        url = "git@github.com:o/r.git"
        self.assertEqual(release.redact(url), url)


class FakeAPI:
    """Serves a scripted sequence of check-run / status payloads."""

    def __init__(self, polls):
        self.polls = list(polls)
        self.calls = 0

    def __call__(self, path, method="GET", body=None, tok=None):
        if "/check-runs" in path:
            self.calls += 1
            index = min(self.calls - 1, len(self.polls) - 1)
            return {"check_runs": self.polls[index]}
        if path.endswith("/status") or "/status?" in path:
            return {"statuses": []}
        raise AssertionError(f"unexpected API call: {path}")


def run(name, status="completed", conclusion="success"):
    return {"name": name, "status": status, "conclusion": conclusion}


class WaitForChecks(unittest.TestCase):
    def setUp(self):
        self.real_api, self.real_sleep = release.api, release.time.sleep
        release.time.sleep = lambda _seconds: None

    def tearDown(self):
        release.api, release.time.sleep = self.real_api, self.real_sleep

    def test_waits_for_the_matrix_to_finish_appearing(self):
        """The regression that matters: one green job is not a green build.

        GitHub creates check runs as jobs are queued, so an early snapshot can
        show a single finished job while the one that fails does not exist yet.
        """
        release.api = FakeAPI([
            [run("build (0.158.0)")],
            [run("build (0.158.0)"), run("build (0.163.3)", conclusion="failure")],
        ])
        with self.assertRaises(SystemExit) as caught:
            release.wait_for_checks("o/r", "abc", "tok")
        self.assertIn("1 check(s) failed", str(caught.exception))

    def test_passes_once_the_set_is_stable_and_green(self):
        both = [run("build (0.158.0)"), run("build (0.163.3)")]
        release.api = FakeAPI([both, both])
        release.wait_for_checks("o/r", "abc", "tok")

    def test_fails_fast_on_a_failed_check(self):
        release.api = FakeAPI([[run("build", conclusion="failure")]])
        with self.assertRaises(SystemExit) as caught:
            release.wait_for_checks("o/r", "abc", "tok")
        self.assertIn("failed", str(caught.exception))

    def test_waits_out_a_pending_check(self):
        release.api = FakeAPI([
            [run("build", status="in_progress", conclusion=None)],
            [run("build")],
            [run("build")],
        ])
        release.wait_for_checks("o/r", "abc", "tok")

    def test_accepts_neutral_and_skipped(self):
        green = [run("build"), run("optional", conclusion="skipped")]
        release.api = FakeAPI([green, green])
        release.wait_for_checks("o/r", "abc", "tok")

    def test_sees_legacy_commit_statuses(self):
        """Netlify reports through the Status API, invisible to /check-runs."""
        def fake(path, method="GET", body=None, tok=None):
            if "/check-runs" in path:
                return {"check_runs": [run("build")]}
            return {"statuses": [
                {"context": "netlify/deploy-preview", "state": "failure"}
            ]}
        release.api = fake
        with self.assertRaises(SystemExit) as caught:
            release.wait_for_checks("o/r", "abc", "tok")
        self.assertIn("netlify/deploy-preview", str(caught.exception))


class EmptyAPIResponse(unittest.TestCase):
    """DELETE answers 204 with no body, which json.load alone would choke on."""

    def fake_urlopen(self, payload):
        import io
        real = release.urllib.request.urlopen
        self.addCleanup(setattr, release.urllib.request, "urlopen", real)
        release.urllib.request.urlopen = lambda request, timeout=None: io.BytesIO(payload)

    def test_returns_none_for_an_empty_body(self):
        self.fake_urlopen(b"")
        self.assertIsNone(release.api("/repos/o/r/git/refs/heads/x", "DELETE", tok="t"))

    def test_returns_none_for_a_whitespace_body(self):
        self.fake_urlopen(b"\n")
        self.assertIsNone(release.api("/repos/o/r/git/refs/heads/x", "DELETE", tok="t"))

    def test_still_parses_a_json_body(self):
        self.fake_urlopen(b'{"sha": "abc"}')
        self.assertEqual(release.api("/repos/o/r/pulls/1", tok="t"), {"sha": "abc"})


class DeleteRemoteBranch(unittest.TestCase):
    def setUp(self):
        real = release.api
        self.addCleanup(setattr, release, "api", real)

    def test_deletes_the_branch_via_the_refs_endpoint(self):
        calls = []

        def fake(path, method="GET", body=None, tok=None):
            calls.append((method, path))
            return None

        release.api = fake
        release.delete_remote_branch("o/r", "release/v1.0.0", "tok")
        self.assertEqual(
            calls, [("DELETE", "/repos/o/r/git/refs/heads/release/v1.0.0")]
        )

    def test_tolerates_a_branch_that_is_already_gone(self):
        def fake(path, method="GET", body=None, tok=None):
            raise release.NotFound(path)

        release.api = fake
        release.delete_remote_branch("o/r", "release/v1.0.0", "tok")

    def test_never_fails_the_release_over_a_leftover_branch(self):
        """The tag is already pushed by this point — litter is not a failure."""
        def fake(path, method="GET", body=None, tok=None):
            raise release.Abort("HTTP 403\nforbidden")

        release.api = fake
        release.delete_remote_branch("o/r", "release/v1.0.0", "tok")


class Rollback(unittest.TestCase):
    """Exercises the failure path against a real git repo.

    This is the code that runs when a release has already started going wrong,
    so "it looked right" is not good enough — the states it leaves behind are
    what the next run has to start from.
    """

    def setUp(self):
        import subprocess
        import tempfile
        self.previous_cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.chdir, self.previous_cwd)
        os.chdir(self.tmp.name)

        def run(*args):
            subprocess.run(args, check=True, capture_output=True)

        run("git", "init", "-b", "main")
        run("git", "config", "user.email", "test@example.com")
        run("git", "config", "user.name", "Test")
        with open("CHANGELOG.md", "w", encoding="utf-8") as handle:
            handle.write("# Changelog\n")
        run("git", "add", "CHANGELOG.md")
        run("git", "commit", "-m", "initial")

    def start_a_release(self):
        """Reach the state release.py is in just after committing the bump."""
        release.git("checkout", "-b", "release/v1.0.0")
        release.write_text("CHANGELOG.md", "# Changelog\n\n## [1.0.0]\n")
        release.git("add", "CHANGELOG.md")
        release.git("commit", "-m", "chore(release): v1.0.0")

    def test_nothing_pushed_returns_to_main_and_deletes_the_branch(self):
        self.start_a_release()
        release.rollback("release/v1.0.0", pushed=False, remote="origin")

        self.assertEqual(release.git("rev-parse", "--abbrev-ref", "HEAD"), "main")
        self.assertEqual(release.git("branch", "--list", "release/v1.0.0"), "")
        self.assertEqual(release.git("status", "--porcelain"), "")
        self.assertEqual(release.read_text("CHANGELOG.md"), "# Changelog\n")

    def test_pushed_returns_to_main_but_keeps_the_branch(self):
        """The remote branch and its PR are where a red build gets fixed."""
        self.start_a_release()
        release.rollback("release/v1.0.0", pushed=True, remote="origin")

        self.assertEqual(release.git("rev-parse", "--abbrev-ref", "HEAD"), "main")
        self.assertIn("release/v1.0.0", release.git("branch", "--list", "release/v1.0.0"))

    def test_discards_an_uncommitted_changelog_edit(self):
        """A failure between writing the file and committing it leaves the
        tree dirty; preflight guarantees nothing else in it is ours to lose."""
        release.git("checkout", "-b", "release/v1.0.0")
        release.write_text("CHANGELOG.md", "# Changelog\n\nhalf-written\n")
        release.rollback("release/v1.0.0", pushed=False, remote="origin")

        self.assertEqual(release.git("rev-parse", "--abbrev-ref", "HEAD"), "main")
        self.assertEqual(release.git("status", "--porcelain"), "")

    def test_is_safe_when_the_branch_was_never_created(self):
        release.rollback("release/v1.0.0", pushed=False, remote="origin")
        self.assertEqual(release.git("rev-parse", "--abbrev-ref", "HEAD"), "main")


if __name__ == "__main__":
    unittest.main(verbosity=2)
