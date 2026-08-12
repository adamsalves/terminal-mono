# Releasing

Cutting a release is one command:

```bash
./scripts/release.py 0.2.3
```

That promotes the changelog, opens the release PR, waits for CI, merges it, and
pushes the tag. A workflow then publishes the GitHub Release. Everything below
is context for when you need to deviate or something breaks.

## Before the first run

**The `origin` remote must be able to push.** Check with `git push --dry-run
origin main`. If it asks for a username and fails, the HTTPS remote has no
stored credentials — switch it to SSH:

```bash
git remote set-url origin git@github.com:adamsalves/terminal-mono.git
```

(Or point the script elsewhere for one run: `REMOTE=git@github.com:adamsalves/terminal-mono.git ./scripts/release.py 0.2.3`.)

**An API token must be reachable.** The script reads `$GITHUB_TOKEN`, and falls
back to the GitHub CLI's stored credentials at `~/.config/gh/hosts.yml` or
`~/snap/gh/current/.config/gh/hosts.yml`. It needs `repo` scope — it opens and
merges a PR. The token file is read directly, so a broken `gh` binary does not
matter, but a token that was never created does.

Nothing else is required: Python 3 standard library and git, no `jq`, no
`gh` locally, no packages to install.

## Choosing the number

[SemVer](https://semver.org/), from the point of view of a site that consumes
the theme:

| bump | when |
|---|---|
| **patch** — `0.2.2` → `0.2.3` | bug fixes, CSS corrections, internal tooling, docs |
| **minor** — `0.2.3` → `0.3.0` | new params, new partials, new features — existing sites keep working |
| **major** — `0.3.0` → `1.0.0` | a consumer must change their config or templates to upgrade |

Renaming or removing a `param`, changing a partial's contract, or dropping a
CSS class a consumer might override is breaking, even if the theme still builds.

## What the command does

1. **Preflight.** Refuses to continue unless the working tree is clean, you are
   on `main`, `main` is level with the remote, the tag does not already exist
   locally or remotely, and `[Unreleased]` actually has entries. Nothing is
   written until every check passes.
2. **Promotes the changelog.** Inserts `## [X.Y.Z] — <today>` under
   `[Unreleased]`, then rewrites the link references at the bottom so
   `[Unreleased]` compares from the new tag and `[X.Y.Z]` compares from the
   previous one.
3. **Opens the release PR** from `release/vX.Y.Z` with a single commit,
   `chore(release): vX.Y.Z`.
4. **Waits for CI.** If any check fails it stops and leaves the branch and PR
   open so you can fix and re-run.
5. **Merges** the PR with a merge commit, matching the existing history.
6. **Tags** the merge commit with an annotated `vX.Y.Z` and pushes it.
7. **`release.yml` publishes the GitHub Release**, using that version's
   changelog section as the body plus a compare link.

Preview the whole thing without touching anything:

```bash
./scripts/release.py 0.2.3 --dry-run
```

Other flags: `--yes` skips the confirmation prompt (for unattended runs),
`--no-merge` stops after opening the PR if you want to review it yourself.

## Tags and Releases are different things

A git tag is a pointer in the repository. A GitHub Release is a separate object
built on top of a tag, and it is what the repo sidebar, the "Latest" badge and
the Releases page actually read. Pushing a tag does **not** create one.

This bit the project twice — `v0.1.0` and `v0.2.2` were both tagged with no
Release, so the front page kept advertising an older version. `release.yml`
exists so the tag push is the only step that has to be remembered.

To preview a release body before cutting anything:

```bash
./scripts/release-notes.py 0.2.3
```

That prints exactly what the workflow will publish.

## When something goes wrong

**Preflight refused.** Read the message; each check names what to fix. The most
common one is `[Unreleased]` being empty — write the changelog entries first.

**CI failed on the release PR.** The branch and PR are still open. Fix on
`release/vX.Y.Z`, push, and let CI re-run; then merge and tag by hand:

```bash
git checkout main && git pull
git tag -a v0.2.3 -m "Terminal Mono v0.2.3"
git push origin v0.2.3
```

**The PR merged but the tag was not pushed.** Run exactly the three commands
above — the script tags the merge commit, so a plain `main` checkout is right.

**The tag was pushed but no Release appeared.** Check the Release workflow in
the Actions tab. The usual cause is a missing `## [X.Y.Z]` section, which means
the release commit did not land before the tag. Fix the changelog on `main`,
then re-run the workflow, or publish by hand:

```bash
./scripts/release-notes.py 0.2.3 > /tmp/notes.md
gh release create v0.2.3 --title v0.2.3 --notes-file /tmp/notes.md --latest
```

**You need to undo a tag that was pushed by mistake.** Delete the Release
first (it keeps the tag alive otherwise), then the tag:

```bash
gh release delete v0.2.3 --yes
git push origin :refs/tags/v0.2.3
git tag -d v0.2.3
```

Only do this if nobody has pulled the tag yet. A consumer pinning the theme by
tag would see it vanish.

## Doing it entirely by hand

The script automates this sequence and nothing more:

```bash
git checkout main && git pull
git checkout -b release/v0.2.3
# edit CHANGELOG.md: add "## [0.2.3] — <today>" under [Unreleased],
# and update the compare links at the bottom
git commit -am "chore(release): v0.2.3"
git push -u origin release/v0.2.3
# open the PR, wait for CI, merge it
git checkout main && git pull
git tag -a v0.2.3 -m "Terminal Mono v0.2.3"
git push origin v0.2.3
```

## After the release

The demo at <https://adamsalves.github.io/terminal-mono/> redeploys on the push
to `main`, so it is current as soon as the release PR merges.

Sites that vendor the theme as a git submodule do not update themselves. In
each one:

```bash
git submodule update --remote themes/terminal-mono
git commit -am "chore: bump terminal-mono to v0.2.3"
```

Sites using Hugo Modules take `hugo mod get -u github.com/adamsalves/terminal-mono`.
