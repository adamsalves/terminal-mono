#!/usr/bin/env python3
"""Cut a release of the theme, end to end.

    ./scripts/release.py 0.2.3

Promotes the CHANGELOG's [Unreleased] section to the new version, opens the
release PR, waits for CI, merges it, and pushes the annotated tag. The Release
workflow then publishes the GitHub Release from the same CHANGELOG section.

Options:
    --dry-run    Show every step and the CHANGELOG diff; change nothing.
    --yes        Skip the confirmation prompt.
    --no-merge   Stop after opening the PR (merge and tag by hand).

Needs only Python 3 and git. The API token comes from $GITHUB_TOKEN, falling
back to the GitHub CLI's stored credentials. Pushes go to $REMOTE (default
"origin") — see RELEASING.md if that remote cannot authenticate.
"""

import argparse
import datetime as dt
import difflib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

CHANGELOG = "CHANGELOG.md"
API = "https://api.github.com"
POLL_SECONDS = 10
CI_TIMEOUT_SECONDS = 900


# ---------------------------------------------------------------- utilities

class Abort(SystemExit):
    def __init__(self, message):
        super().__init__(f"\033[31maborted:\033[0m {message}")


def step(message):
    print(f"\033[36m==>\033[0m {message}")


def note(message):
    print(f"    {message}")


def git(*args, check=True):
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise Abort(f"git {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    candidates = [
        os.path.expanduser("~/.config/gh/hosts.yml"),
        os.path.expanduser("~/snap/gh/current/.config/gh/hosts.yml"),
    ]
    for path in candidates:
        if os.path.exists(path):
            found = re.search(r"^\s*oauth_token:\s*(\S+)", open(path).read(), re.M)
            if found:
                return found.group(1)
    raise Abort(
        "no API token. Set GITHUB_TOKEN, or sign in with the GitHub CLI so a "
        f"token exists in one of: {', '.join(candidates)}"
    )


def api(path, method="GET", body=None, tok=None):
    request = urllib.request.Request(
        f"{API}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "terminal-mono-release",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode()[:400]
        raise Abort(f"{method} {path} -> HTTP {error.code}\n{detail}")


def repo_slug(remote):
    url = git("remote", "get-url", remote)
    found = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    if not found:
        raise Abort(f'remote "{remote}" is not a GitHub URL: {url}')
    return found.group(1), url


# ----------------------------------------------------------------- changelog

def promote_changelog(text, version, today, repo):
    """Insert the new version heading and chain the compare links."""
    if not re.search(r"^## \[Unreleased\]\s*$", text, re.M):
        raise Abort(f"{CHANGELOG} has no '## [Unreleased]' heading")
    if re.search(rf"^## \[{re.escape(version)}\]", text, re.M):
        raise Abort(f"{CHANGELOG} already has a '## [{version}]' section")

    body = re.search(r"^## \[Unreleased\]\s*$\n(.*?)(?=^## \[)", text, re.M | re.S)
    if not body or not body.group(1).strip():
        raise Abort(
            "nothing to release: the [Unreleased] section is empty. "
            "Add the entries first, then run this again."
        )

    text = re.sub(
        r"^(## \[Unreleased\]\s*$\n)",
        rf"\1\n## [{version}] — {today}\n",
        text,
        count=1,
        flags=re.M,
    )

    link = re.search(
        r"^\[Unreleased\]:\s*(\S+)/compare/(v\S+)\.\.\.HEAD\s*$", text, re.M
    )
    if not link:
        raise Abort(f"{CHANGELOG} has no '[Unreleased]: .../compare/vX...HEAD' link")
    base, previous = link.group(1), link.group(2)
    text = text.replace(
        link.group(0),
        f"[Unreleased]: {base}/compare/v{version}...HEAD\n"
        f"[{version}]: {base}/compare/{previous}...v{version}",
        1,
    )
    return text, previous


# ------------------------------------------------------------------ preflight

def preflight(version, remote, tok, slug):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise Abort(f"version must look like 1.2.3, got {version!r}")

    if git("status", "--porcelain"):
        raise Abort("working tree is dirty — commit or stash first")

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        raise Abort(f"must run from main, currently on {branch!r}")

    if git("tag", "-l", f"v{version}"):
        raise Abort(f"tag v{version} already exists locally")

    git("fetch", remote, "main", "--tags")
    local, upstream = git("rev-parse", "HEAD"), git("rev-parse", "FETCH_HEAD")
    if local != upstream:
        raise Abort(
            f"main is out of sync with {remote} "
            f"(local {local[:7]}, remote {upstream[:7]}) — pull or push first"
        )

    existing = [t["name"] for t in api(f"/repos/{slug}/tags?per_page=100", tok=tok)]
    if f"v{version}" in existing:
        raise Abort(f"tag v{version} already exists on {remote}")

    note(f"main is clean and level with {remote} at {local[:7]}")


# ----------------------------------------------------------------------- CI

def wait_for_checks(slug, sha, tok):
    deadline = time.time() + CI_TIMEOUT_SECONDS
    seen = False
    while time.time() < deadline:
        runs = api(f"/repos/{slug}/commits/{sha}/check-runs", tok=tok)["check_runs"]
        if runs:
            seen = True
            pending = [r for r in runs if r["status"] != "completed"]
            if not pending:
                ok = ("success", "neutral", "skipped")
                bad = [r for r in runs if r["conclusion"] not in ok]
                for run in runs:
                    mark = "\033[32m✓\033[0m" if run["conclusion"] in ok else "\033[31m✗\033[0m"
                    note(f"{mark} {run['name']}: {run['conclusion']}")
                if bad:
                    raise Abort(
                        f"{len(bad)} check(s) failed — fix them and re-run; "
                        f"the release branch and PR are still open"
                    )
                return
            note(f"waiting on {len(pending)} check(s): "
                 f"{', '.join(r['name'] for r in pending)}")
        elif not seen:
            note("waiting for checks to be created…")
        time.sleep(POLL_SECONDS)
    raise Abort(f"checks did not finish within {CI_TIMEOUT_SECONDS}s")


# ---------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(add_help=True, description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", help="the new version, without the leading v (e.g. 0.2.3)")
    parser.add_argument("--dry-run", action="store_true", help="change nothing")
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    parser.add_argument("--no-merge", action="store_true", help="stop after opening the PR")
    args = parser.parse_args()

    root = git("rev-parse", "--show-toplevel")
    os.chdir(root)

    version = args.version.lstrip("v")
    remote = os.environ.get("REMOTE", "origin")
    tag = f"v{version}"
    branch = f"release/{tag}"
    today = dt.date.today().isoformat()

    tok = token()
    slug, remote_url = repo_slug(remote)

    step(f"Releasing {tag} of {slug} via {remote} ({remote_url})")
    preflight(version, remote, tok, slug)

    original = open(CHANGELOG).read()
    updated, previous = promote_changelog(original, version, today, slug)
    diff = "".join(difflib.unified_diff(
        original.splitlines(keepends=True), updated.splitlines(keepends=True),
        fromfile=f"a/{CHANGELOG}", tofile=f"b/{CHANGELOG}"))
    step(f"CHANGELOG.md: [Unreleased] -> [{version}] — {today} (previous: {previous})")
    print(diff)

    if args.dry_run:
        step("Dry run — stopping here. Would have:")
        note(f"committed the diff above on {branch}")
        note(f"pushed {branch} to {remote} and opened a PR against main")
        note("waited for CI, merged the PR")
        note(f"tagged the merge commit {tag} and pushed it")
        note("let .github/workflows/release.yml publish the GitHub Release")
        return

    if not args.yes:
        answer = input(f"\nCut {tag}? This merges to main and pushes a tag. [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            raise Abort("cancelled")

    step(f"Committing on {branch}")
    git("checkout", "-b", branch)
    open(CHANGELOG, "w").write(updated)
    git("add", CHANGELOG)
    git("commit", "-m", f"chore(release): {tag}")

    step(f"Pushing {branch} to {remote}")
    git("push", remote, branch)

    step("Opening the release PR")
    pull = api(f"/repos/{slug}/pulls", "POST", {
        "title": f"chore(release): {tag}",
        "head": branch,
        "base": "main",
        "body": (
            f"Promotes `[Unreleased]` to **{tag}** and chains the compare links.\n\n"
            f"Generated by `scripts/release.py`. The tag is pushed once this merges "
            f"and CI is green; `.github/workflows/release.yml` then publishes the "
            f"GitHub Release from the `## [{version}]` section.\n\n"
            f"**Full changelog:** https://github.com/{slug}/compare/{previous}...{tag}\n"
        ),
    }, tok=tok)
    note(pull["html_url"])

    if args.no_merge:
        step("--no-merge — stopping here")
        note(f"merge the PR, then: git tag -a {tag} -m 'Terminal Mono {tag}' "
             f"&& git push {remote} {tag}")
        return

    step("Waiting for CI")
    wait_for_checks(slug, pull["head"]["sha"], tok)

    step("Merging the release PR")
    merge = api(f"/repos/{slug}/pulls/{pull['number']}/merge", "PUT", {
        "merge_method": "merge",
        "sha": pull["head"]["sha"],
        "commit_title": f"Merge pull request #{pull['number']} from {slug.split('/')[0]}/{branch}",
        "commit_message": f"chore(release): {tag}",
    }, tok=tok)
    note(f"merge commit {merge['sha'][:7]}")

    step(f"Tagging {tag}")
    git("checkout", "main")
    git("fetch", remote, "main")
    git("merge", "--ff-only", "FETCH_HEAD")
    head = git("rev-parse", "HEAD")
    if head != merge["sha"]:
        raise Abort(f"main is at {head[:7]}, expected the merge commit {merge['sha'][:7]}")
    git("tag", "-a", tag, "-m", f"Terminal Mono {tag}")
    git("push", remote, tag)

    step("Waiting for the Release workflow")
    deadline = time.time() + 300
    while time.time() < deadline:
        try:
            release = api(f"/repos/{slug}/releases/tags/{tag}", tok=tok)
            step(f"Released: {release['html_url']}")
            return
        except Abort:
            time.sleep(POLL_SECONDS)
    note("the Release workflow has not published yet — check the Actions tab")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\naborted: interrupted")
