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
RELEASE_TIMEOUT_SECONDS = 300
API_TIMEOUT_SECONDS = 30
# A check run is only trusted once the same set has come back green twice.
# GitHub creates runs as jobs are queued, not atomically.
REQUIRED_STABLE_POLLS = 2
CHECK_OK = ("success", "neutral", "skipped")

# A section ends at the next version heading, at the link-reference block that
# closes the file, or at EOF. Kept identical to release-notes.py: if the two
# disagree about where a section stops, the notes and the changelog diverge.
SECTION_END = r"(?=^## \[|^\[[^\]]+\]:\s|\Z)"


# ---------------------------------------------------------------- utilities

class Abort(SystemExit):
    def __init__(self, message):
        super().__init__(f"\033[31maborted:\033[0m {message}")


class NotFound(Exception):
    """A 404 from the API — a state to poll past, not a failure to report."""


def redact(text):
    """Blank any credential embedded in a URL before it reaches the terminal.

    `git remote get-url` returns the token verbatim when the remote carries
    one, and both the banner and the git error path echo it.
    """
    return re.sub(r"(https?://)[^@/\s]+@", r"\1***@", text)


def step(message):
    print(f"\033[36m==>\033[0m {message}")


def note(message):
    print(f"    {message}")


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def git(*args, check=True):
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise Abort(redact(f"git {' '.join(args)}\n{result.stderr.strip()}"))
    return result.stdout.strip()


def github_com_token(hosts_yml):
    """The oauth_token under the github.com: block of a gh hosts.yml, or None.

    Scoped to that block deliberately. A hosts.yml can also hold an enterprise
    host, and the first token in the file is not necessarily the one
    api.github.com accepts — sending the other one there leaks it to a server
    that has no business seeing it.
    """
    block = re.search(r"^github\.com:\s*$\n(.*?)(?=^\S|\Z)", hosts_yml, re.M | re.S)
    if not block:
        return None
    found = re.search(r"^\s+oauth_token:\s*(\S+)", block.group(1), re.M)
    return found.group(1) if found else None


def token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    candidates = [
        os.path.expanduser("~/.config/gh/hosts.yml"),
        os.path.expanduser("~/snap/gh/current/.config/gh/hosts.yml"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        found = github_com_token(read_text(path))
        if found:
            return found
    raise Abort(
        "no API token. Set GITHUB_TOKEN, or sign in with the GitHub CLI so a "
        f"github.com token exists in one of: {', '.join(candidates)}"
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
        with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
            payload = response.read()
        # DELETE answers 204 No Content; there is nothing to parse.
        return json.loads(payload) if payload.strip() else None
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise NotFound(path)
        detail = redact(error.read().decode(errors="replace")[:400])
        raise Abort(f"{method} {path} -> HTTP {error.code}\n{detail}")
    except urllib.error.URLError as error:
        raise Abort(f"{method} {path} -> network error: {error.reason}")
    except TimeoutError:
        raise Abort(f"{method} {path} -> timed out after {API_TIMEOUT_SECONDS}s")
    except json.JSONDecodeError as error:
        raise Abort(f"{method} {path} -> malformed JSON response: {error}")


def slug_from_url(url):
    """The owner/name in a GitHub remote URL, SSH or HTTPS, or None."""
    found = re.search(r"github\.com[:/](.+?)(?:\.git)?/?$", url)
    return found.group(1) if found else None


def repo_slug(remote):
    """Resolve $REMOTE, which may be a remote name or a bare URL.

    git push takes either, so RELEASING.md offers a URL for the case where the
    configured remote cannot authenticate; get-url only takes a name, so fall
    back to reading the value as the URL it already is.
    """
    url = git("remote", "get-url", remote, check=False) or remote
    slug = slug_from_url(url)
    if not slug:
        raise Abort(f'"{remote}" is not a GitHub remote or URL: {redact(url)}')
    return slug, redact(url)


# ----------------------------------------------------------------- changelog

def promote_changelog(text, version, today):
    """Insert the new version heading and chain the compare links.

    The compare URLs are rebuilt from the existing [Unreleased] link rather
    than from the repo slug, so a fork keeps pointing at its own remote.
    """
    if not re.search(r"^## \[Unreleased\]\s*$", text, re.M):
        raise Abort(f"{CHANGELOG} has no '## [Unreleased]' heading")
    if re.search(rf"^## \[{re.escape(version)}\]", text, re.M):
        raise Abort(f"{CHANGELOG} already has a '## [{version}]' section")

    body = re.search(rf"^## \[Unreleased\]\s*$\n(.*?){SECTION_END}", text, re.M | re.S)
    if not body or not body.group(1).strip():
        raise Abort(
            "nothing to release: the [Unreleased] section is empty. "
            "Add the entries first, then run this again."
        )

    # Consume the blank lines that followed [Unreleased] and re-emit exactly
    # one on each side, so the new section is spaced like every existing one
    # instead of accreting a stray blank line per release.
    # [ \t]* rather than \s*: \s eats newlines, so the capture would swallow
    # the blank line below the heading and re-emitting one would double it.
    text = re.sub(
        r"^(## \[Unreleased\][ \t]*\n)\n*",
        rf"\1\n## [{version}] — {today}\n\n",
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

def preflight(version, remote, tag):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise Abort(f"version must look like 1.2.3, got {version!r}")

    if git("status", "--porcelain"):
        raise Abort("working tree is dirty — commit or stash first")

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        raise Abort(f"must run from main, currently on {branch!r}")

    # --tags brings the remote tags into the local namespace, so the single
    # check below covers "exists here" and "exists there" at once.
    git("fetch", remote, "main", "--tags")
    if git("tag", "-l", tag):
        raise Abort(f"tag {tag} already exists (locally or on {remote})")

    local, upstream = git("rev-parse", "HEAD"), git("rev-parse", "FETCH_HEAD")
    if local != upstream:
        raise Abort(
            f"main is out of sync with {remote} "
            f"(local {local[:7]}, remote {upstream[:7]}) — pull or push first"
        )

    note(f"main is clean and level with {remote} at {local[:7]}")


# ----------------------------------------------------------------------- CI

def check_states(slug, sha, tok):
    """Every check on a commit, as (pending, failed, passed) name lists.

    Reads the Status API as well as Check Runs. Netlify and other older
    integrations report through commit statuses, which /check-runs never
    returns — gating on check runs alone is blind to them.
    """
    pending, failed, passed = [], [], []

    runs = api(f"/repos/{slug}/commits/{sha}/check-runs?per_page=100", tok=tok)
    for run in runs["check_runs"]:
        if run["status"] != "completed":
            pending.append(run["name"])
        elif run["conclusion"] in CHECK_OK:
            passed.append(run["name"])
        else:
            failed.append(f"{run['name']} ({run['conclusion']})")

    combined = api(f"/repos/{slug}/commits/{sha}/status?per_page=100", tok=tok)
    for status in combined["statuses"]:
        if status["state"] == "pending":
            pending.append(status["context"])
        elif status["state"] == "success":
            passed.append(status["context"])
        else:
            failed.append(f"{status['context']} ({status['state']})")

    return pending, failed, passed


def wait_for_checks(slug, sha, tok):
    """Block until every check on `sha` has completed successfully.

    Waits for the set of checks to stop growing before trusting it: "everything
    I can see is complete" is not the same as "the build is green" when the
    matrix job that fails has not been created yet.
    """
    deadline = time.time() + CI_TIMEOUT_SECONDS
    stable, previous = 0, None

    while time.time() < deadline:
        pending, failed, passed = check_states(slug, sha, tok)
        names = sorted(pending + failed + passed)

        if failed:
            for name in failed:
                note(f"\033[31m✗\033[0m {name}")
            raise Abort(
                f"{len(failed)} check(s) failed: {', '.join(failed)} — fix them "
                f"and re-run; the release branch and PR are still open"
            )

        if not names:
            note("waiting for checks to be created…")
        elif pending:
            note(f"waiting on {len(pending)} check(s): {', '.join(sorted(pending))}")
        else:
            stable = stable + 1 if names == previous else 1
            if stable >= REQUIRED_STABLE_POLLS:
                for name in sorted(passed):
                    note(f"\033[32m✓\033[0m {name}")
                return
            note(f"{len(names)} check(s) green — confirming the set is complete…")

        previous = names
        time.sleep(POLL_SECONDS)

    raise Abort(f"checks did not finish within {CI_TIMEOUT_SECONDS}s")


def verify_mergeable(slug, number, tok):
    """Confirm GitHub itself considers the PR mergeable before merging it.

    `mergeable` is computed asynchronously and is null until GitHub finishes,
    so poll past that. This is the check that respects branch protection:
    "blocked" means a required check or review is still in the way, which is
    worth saying plainly rather than surfacing as a raw 405 from the merge.
    """
    deadline = time.time() + RELEASE_TIMEOUT_SECONDS
    while time.time() < deadline:
        pull = api(f"/repos/{slug}/pulls/{number}", tok=tok)
        if pull["mergeable"] is None:
            time.sleep(POLL_SECONDS)
            continue
        state = pull.get("mergeable_state", "unknown")
        if not pull["mergeable"] or state in ("blocked", "dirty", "behind", "draft"):
            raise Abort(
                f"PR #{number} is not mergeable (state: {state}) — "
                f"the branch and PR are still open"
            )
        note(f"mergeable (state: {state})")
        return
    raise Abort(f"GitHub never reported a mergeable state for PR #{number}")


def delete_remote_branch(slug, branch, tok):
    """Remove the merged release branch from the remote.

    Best effort by design. It runs only after the tag is pushed, so the release
    is already complete and a branch that outlives it is litter, not a failure
    — worth reporting, never worth aborting over. Without this the local copy
    gets cleaned up and the remote one accumulates, one per release.
    """
    try:
        api(f"/repos/{slug}/git/refs/heads/{branch}", "DELETE", tok=tok)
        note(f"deleted {branch} from {slug}")
    except NotFound:
        note(f"{branch} was already gone from {slug}")
    except Abort:
        note(f"could not delete {branch} from {slug} — remove it by hand")


# ------------------------------------------------------------------ recovery

def rollback(branch, pushed, remote):
    """Undo what is still private; name what is not.

    Anything that reached the remote is left alone — an open PR is the
    documented place to fix a red build from. The local branch only survives
    when its remote twin does, so a retry starts from a clean main either way
    instead of failing preflight and then failing again on checkout -b.
    """
    if git("rev-parse", "--abbrev-ref", "HEAD", check=False) == branch:
        # Only our own CHANGELOG edit can be in the tree: preflight refused to
        # start until it was clean.
        git("checkout", "--force", "main", check=False)
    if pushed:
        note(f"{branch} and its PR are still open on {remote} — see RELEASING.md")
        note(f"the local branch is kept to match; drop it with: git branch -D {branch}")
    else:
        git("branch", "-D", branch, check=False)
        note(f"rolled back: {branch} deleted, back on main, nothing pushed")


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
    # UTC, matching the TZ the workflows pin, so the changelog date cannot
    # disagree with the date on the tag it describes.
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()

    tok = token()
    slug, remote_url = repo_slug(remote)

    step(f"Releasing {tag} of {slug} via {remote} ({remote_url})")
    preflight(version, remote, tag)

    original = read_text(CHANGELOG)
    updated, previous = promote_changelog(original, version, today)
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
        try:
            answer = input(f"\nCut {tag}? This merges to main and pushes a tag. [y/N] ")
        except EOFError:
            raise Abort("stdin is not a terminal — re-run with --yes to confirm up front")
        if answer.strip().lower() not in ("y", "yes"):
            raise Abort("cancelled")

    if git("branch", "--list", branch):
        raise Abort(
            f"branch {branch} already exists locally — a previous run left it "
            f"behind. Remove it with: git branch -D {branch}"
        )

    step(f"Committing on {branch}")
    git("checkout", "-b", branch)
    pushed = False
    try:
        write_text(CHANGELOG, updated)
        git("add", CHANGELOG)
        git("commit", "-m", f"chore(release): {tag}")

        step(f"Pushing {branch} to {remote}")
        git("push", remote, branch)
        pushed = True

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
            note(f"merge the PR, then: git checkout main && git pull && "
                 f"git tag -a {tag} -m 'Terminal Mono {tag}' && git push {remote} {tag}")
            return

        step("Waiting for CI")
        wait_for_checks(slug, pull["head"]["sha"], tok)
        verify_mergeable(slug, pull["number"], tok)

        step("Merging the release PR")
        merge = api(f"/repos/{slug}/pulls/{pull['number']}/merge", "PUT", {
            "merge_method": "merge",
            "sha": pull["head"]["sha"],
            "commit_title": f"Merge pull request #{pull['number']} from {slug.split('/')[0]}/{branch}",
            "commit_message": f"chore(release): {tag}",
        }, tok=tok)
        note(f"merge commit {merge['sha'][:7]}")
    except BaseException:
        rollback(branch, pushed, remote)
        raise

    step(f"Tagging {tag}")
    git("checkout", "main")
    git("branch", "-D", branch, check=False)
    git("fetch", remote, "main")
    git("merge", "--ff-only", "FETCH_HEAD")
    head = git("rev-parse", "HEAD")
    if head != merge["sha"]:
        raise Abort(f"main is at {head[:7]}, expected the merge commit {merge['sha'][:7]}")
    git("tag", "-a", tag, "-m", f"Terminal Mono {tag}")
    git("push", remote, tag)

    # The release is complete from here on; tidying cannot fail it.
    delete_remote_branch(slug, branch, tok)

    step("Waiting for the Release workflow")
    deadline = time.time() + RELEASE_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            release = api(f"/repos/{slug}/releases/tags/{tag}", tok=tok)
        except NotFound:
            time.sleep(POLL_SECONDS)
            continue
        step(f"Released: {release['html_url']}")
        return
    note("the Release workflow has not published yet — check the Actions tab")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        sys.exit("\naborted: interrupted")
