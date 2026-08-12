#!/usr/bin/env python3
"""Print the release notes for a version, taken from CHANGELOG.md.

    ./scripts/release-notes.py 0.2.2

Emits that version's CHANGELOG section followed by a compare link against the
previous tag. Used by .github/workflows/release.yml to build the GitHub Release
body, and runnable locally to preview exactly what will be published.
"""

import os
import re
import subprocess
import sys

CHANGELOG = "CHANGELOG.md"
DEFAULT_REPO = "https://github.com/adamsalves/terminal-mono"


def previous_tag(tag):
    """The highest vX.Y.Z tag that is not this one, or None."""
    result = subprocess.run(
        ["git", "tag", "-l", "v[0-9]*.[0-9]*.[0-9]*", "--sort=-v:refname"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return next((t for t in result.stdout.split() if t != tag), None)


def repo_url():
    server = os.environ.get("GITHUB_SERVER_URL")
    slug = os.environ.get("GITHUB_REPOSITORY")
    return f"{server}/{slug}" if server and slug else DEFAULT_REPO


def notes_for(version, changelog_text, tag=None):
    tag = tag or f"v{version}"
    section = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[)",
        changelog_text, re.M | re.S,
    )
    if not section:
        raise SystemExit(
            f"{CHANGELOG} has no '## [{version}]' section — the release commit "
            f"must land before the tag is pushed."
        )
    body = section.group(1).strip()
    if not body:
        raise SystemExit(f"the '## [{version}]' section is empty.")

    previous = previous_tag(tag)
    if previous:
        body += f"\n\n**Full changelog:** {repo_url()}/compare/{previous}...{tag}"
    return body


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <version>   (e.g. 0.2.3)")
    version = sys.argv[1].lstrip("v")
    print(notes_for(version, open(CHANGELOG).read()))


if __name__ == "__main__":
    main()
