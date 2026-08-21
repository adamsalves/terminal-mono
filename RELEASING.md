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

(Or point the script elsewhere for one run — `$REMOTE` takes a remote name or a
URL: `REMOTE=git@github.com:adamsalves/terminal-mono.git ./scripts/release.py 0.2.3`.)

**An API token must be reachable.** The script reads `$GITHUB_TOKEN`, and falls
back to the GitHub CLI's stored credentials at `~/.config/gh/hosts.yml` or
`~/snap/gh/current/.config/gh/hosts.yml` — specifically the token under the
`github.com:` block, not whichever one comes first in the file. It needs `repo`
scope: it opens and merges a PR. The token file is read directly, so a broken
`gh` binary does not matter, but a token that was never created does.

Nothing else is required for a release: Python 3 standard library and git, no
`jq`, no packages to install. `gh` is only needed for the by-hand recovery in
[When something goes wrong](#when-something-goes-wrong), and even there the
Actions tab can do the same job.

## Choosing the number

[SemVer](https://semver.org/), from the point of view of a site that consumes
the theme:

| bump | when |
|---|---|
| **patch** — `0.2.2` → `0.2.3` | bug fixes, CSS corrections, internal tooling, docs |
| **minor** — `0.2.3` → `0.3.0` | new params, new partials, new features — and, while the theme is `0.x`, breaking changes too |
| **major** — `1.0.0` → `2.0.0` | a consumer must change their config or templates to upgrade |

Renaming or removing a `param`, changing a partial's contract, or dropping a
CSS class a consumer might override is breaking, even if the theme still builds.

While the theme is `0.x`, a breaking change goes in the **minor** — `0.3.0` →
`0.4.0`, not `1.0.0`. [SemVer §4](https://semver.org/#spec-item-4) puts major
version zero outside the stability guarantee: the public API is not yet
something a major bump can be said to break. The `Changed` entry in the
changelog carries the migration note instead — what breaks, and what to write
to keep the old behaviour.

`1.0.0` is therefore a decision rather than an arithmetic consequence. It says
the config and partial contracts are stable from that point on — no single
breaking change triggers it, which is why the **major** row above counts from
`1.0.0` and not from `0.x`.

## What the command does

1. **Preflight.** Refuses to continue unless the working tree is clean, you are
   on `main`, `main` is level with the remote, the tag does not already exist
   locally or remotely, and `[Unreleased]` actually has entries. Nothing is
   written until every check passes.
2. **Promotes the changelog.** Inserts `## [X.Y.Z] — <today>` (UTC) under
   `[Unreleased]`, then rewrites the link references at the bottom so
   `[Unreleased]` compares from the new tag and `[X.Y.Z]` compares from the
   previous one.
3. **Opens the release PR** from `release/vX.Y.Z` with a single commit,
   `chore(release): vX.Y.Z`.
4. **Waits for CI.** Gates on check runs *and* legacy commit statuses, and only
   accepts a green result once the set of checks has stopped growing — one
   finished job is not a finished build. Then confirms GitHub itself reports
   the PR as mergeable, so branch protection is respected rather than bypassed.
   If anything fails it stops and leaves the branch and PR open.
5. **Merges** the PR with a merge commit, matching the existing history.
6. **Tags** the merge commit with an annotated `vX.Y.Z` and pushes it.
7. **Deletes the release branch**, locally and on the remote. This runs after
   the tag is pushed, so a failure here only prints a warning — the release is
   already done and a leftover branch is litter, not a broken release.
8. **`release.yml` publishes the GitHub Release**, using that version's
   changelog section as the body plus a compare link.

Preview the changelog diff and every step without writing anything:

```bash
./scripts/release.py 0.2.3 --dry-run
```

`--dry-run` changes nothing locally or remotely, but it is not offline: it
still resolves a token and runs preflight, which queries the remote.

Other flags: `--yes` skips the confirmation prompt (required for unattended
runs — without a terminal the prompt aborts rather than hanging), `--no-merge`
stops after opening the PR if you want to review it yourself.

## If a run fails partway

The script cleans up after itself as far as it safely can:

- **Nothing was pushed yet.** It returns you to `main` and deletes the local
  `release/vX.Y.Z` branch. Fix the cause and run it again.
- **The branch reached the remote.** The branch and PR are left open — that is
  where you fix a red build from — and the local branch is kept to match. It
  still returns you to `main`.

Either way the next run starts from a clean `main`. If a local
`release/vX.Y.Z` is left behind deliberately, preflight says so and names the
command to remove it (`git branch -D release/vX.Y.Z`).

## Tags and Releases are different things

A git tag is a pointer in the repository. A GitHub Release is a separate object
built on top of a tag, and it is what the repo sidebar, the "Latest" badge and
the Releases page actually read. Pushing a tag does **not** create one.

This bit the project twice — `v0.1.0` and `v0.2.2` were both tagged with no
Release, so the front page kept advertising an older version. `release.yml`
exists so the tag push is the only step that has to be remembered.

Which Release carries the "Latest" badge is left to GitHub, which picks it by
version and date. That is deliberate: forcing it would hand the badge to an old
version the moment a Release is backfilled, which is the exact problem above.

To preview a release body before cutting anything:

```bash
./scripts/release-notes.py 0.2.3
```

That prints exactly what the workflow will publish, and works from any
directory in the repo.

## When something goes wrong

**Preflight refused.** Read the message; each check names what to fix. The most
common one is `[Unreleased]` being empty — write the changelog entries first.

**CI failed on the release PR.** The branch and PR are still open, and you are
back on `main`. Fix on `release/vX.Y.Z`, push, and let CI re-run; then merge and
tag by hand:

```bash
git checkout main && git pull
git tag -a v0.2.3 -m "Terminal Mono v0.2.3"
git push origin v0.2.3
```

**The PR merged but the tag was not pushed.** Run exactly the three commands
above — the script tags the merge commit, so a plain `main` checkout is right.

**The tag was pushed but no Release appeared.** Check the Release workflow in
the Actions tab. The usual cause is a missing `## [X.Y.Z]` section, which means
the release commit did not land before the tag was pushed.

Re-running the failed workflow run will not help on its own: it rebuilds from
the commit the tag points at, so a fix made on `main` afterwards is invisible to
it. Either move the tag onto the corrected commit and let the push trigger a
fresh run:

```bash
git checkout main && git pull        # with the CHANGELOG fix already merged
git tag -f -a v0.2.3 -m "Terminal Mono v0.2.3"
git push --force origin v0.2.3
```

…or, if the tag is where you want it, publish from the Actions tab: **Release →
Run workflow**, and give it the tag. That path checks out the tag you name, so
it is also how you backfill a Release for an old version. Failing both, do it
locally:

```bash
./scripts/release-notes.py 0.2.3 > /tmp/notes.md
gh release create v0.2.3 --title v0.2.3 --notes-file /tmp/notes.md
```

Leave `--latest` off. GitHub works it out from the version, and forcing it
would move the badge backwards when the version is an old one.

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

## Changing the tooling

`scripts/test_release.py` covers the parts that decide what gets published —
changelog promotion, note extraction, tag ordering, token scoping and the CI
gate — against the repository's real `CHANGELOG.md`:

```bash
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

`ci.yml` runs it on every pull request, so the release PR validates its own
promoted changelog before it is allowed to merge.

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
