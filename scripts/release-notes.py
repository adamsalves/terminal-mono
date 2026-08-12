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

# A section ends at the next version heading, at the link-reference block that
# closes the file, or at EOF. Stopping only at "^## [" would make the oldest
# section unreadable — there is no heading after it — which is exactly the
# backfill case this script exists to serve.
SECTION_END = r"(?=^## \[|^\[[^\]]+\]:\s|\Z)"


def version_key(tag):
    """(major, minor, patch) for a vX.Y.Z tag, or None if it does not parse."""
    found = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
    return tuple(int(part) for part in found.groups()) if found else None


def previous_tag(tag, tags=None):
    """The highest vX.Y.Z tag strictly below this one, or None.

    Ordered by version rather than "the highest tag that is not this one", so
    publishing an older tag late — a maintenance patch cut after a newer minor,
    or a backfill — still compares forwards instead of producing a reversed
    range like v0.3.0...v0.2.3.
    """
    if tags is None:
        result = subprocess.run(
            ["git", "tag", "-l", "v[0-9]*.[0-9]*.[0-9]*"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return None
        tags = result.stdout.split()

    current = version_key(tag)
    if current is None:
        return None
    lower = []
    for name in tags:
        key = version_key(name)
        if key is not None and key < current:
            lower.append((key, name))
    return max(lower)[1] if lower else None


def repo_url():
    server = os.environ.get("GITHUB_SERVER_URL")
    slug = os.environ.get("GITHUB_REPOSITORY")
    return f"{server}/{slug}" if server and slug else DEFAULT_REPO


def notes_for(version, changelog_text, tag=None, tags=None):
    tag = tag or f"v{version}"
    section = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?){SECTION_END}",
        changelog_text, re.M | re.S,
    )
    if not section:
        present = re.findall(r"^## \[([^\]]+)\]", changelog_text, re.M)
        raise SystemExit(
            f"{CHANGELOG} has no '## [{version}]' section — the release commit "
            f"must land before the tag is pushed. "
            f"Sections present: {', '.join(present) or '(none)'}"
        )
    body = section.group(1).strip()
    if not body:
        raise SystemExit(f"the '## [{version}]' section is empty.")

    previous = previous_tag(tag, tags)
    if previous:
        body += f"\n\n**Full changelog:** {repo_url()}/compare/{previous}...{tag}"
    return body


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <version>   (e.g. 0.2.3)")
    version = sys.argv[1].lstrip("v")

    # CHANGELOG is a repo-relative path, and RELEASING.md invites running this
    # by hand — which nobody does from the repo root every time.
    root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
    )
    if root.returncode == 0:
        os.chdir(root.stdout.strip())

    with open(CHANGELOG, encoding="utf-8") as handle:
        print(notes_for(version, handle.read()))


if __name__ == "__main__":
    main()
