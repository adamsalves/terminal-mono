# Changelog

All notable changes to this theme are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Hero terminal: the section switch reaches the terminal. v0.4.0 taught the hero
  that its "view projects" button must not point at a section that does not
  render, but the terminal directly above it went on typing `ls projects/` and
  listing the repositories of a section the reader could not scroll to. Both
  remaining commands now follow the plan: `ls projects/` follows the `projects`
  section, and `cat stack.txt` follows `about`, which is where the skills live.
- Hero terminal: a command with no output is no longer typed at all. Only the
  blog listing had ever followed that rule; `cat stack.txt` and `ls projects/`
  were unconditional, so a site that filled nothing in — the one CI has been
  building all along — greeted its reader with two commands and two blank lines
  under them. This half is fixed in the script rather than the template, so an
  empty value produces no command whatever put it there. `whoami` is the stated
  exception and always runs: its output is the page's own identity, not a
  section's data, so no switch can empty it.
- Hero terminal: the reserved height follows the commands that actually render.
  It was a constant `12` lines plus one per post, which was right only while all
  three commands always rendered; drop one and the box reserved three lines it
  never filled, leaving a block of dead space under the hero — the same class of
  bug as `section--last` sitting on a section that was no longer last. The
  template now counts the lines it is about to emit and passes them as
  `--hero-lines`, replacing the `--hero-posts` variable and the
  `.term__body--posts` class, which are gone. CI recomputes the count from the
  rendered `data-*` attributes and holds the variable to it.

### Changed
- Hero terminal: `cat stack.txt` now follows `[params.about.skills] enable`,
  which has to be an explicit `true` — an absent key counts as off, the same
  reading the skills block inside the about section and the section index have
  always used. The switch used to hide that block while the terminal above kept
  announcing the same list — one switch that meant two different things
  depending on where you looked. Sites that write `enable = true`, the
  exampleSite among them, are unaffected. A site that lists `items` **without**
  an `enable` key does lose `cat stack.txt`: it was already not rendering the
  skills block, and the terminal now agrees with the page instead of announcing
  a list the reader cannot find.

## [0.4.0] — 2026-08-20

### Added
- Sections: `[[menu.main]]` now drives the order the home page renders its
  sections in, not just the nav. The menu is the page's index — a reader who
  sees "projects · about · experience" at the top expects the page in that
  order — and keeping two lists that are allowed to disagree is an invitation
  for them to. Delete an entry and the section goes with the link, which is the
  answer to "I don't want the experience section" that used to require
  overriding a layout in the consuming site. Non-section identifiers (`blog`,
  external links) stay nav-only, and the hero stays the page header rather than
  a section, so it cannot be moved or removed.
- Sections: every section takes an `enable` switch — `[params.about] enable`,
  `[params.projects]`, `[params.experience]`, `[params.contact]`. It is a veto
  and never a summons: `false` removes the section and its nav link whatever the
  menu says, `true` grants nothing the menu and the section's own content do not
  already grant. Forcing inclusion would rebuild the two defects this release
  closes — a section outside the index, and a section rendered empty. Being an
  ordinary param, it is language-scoped: a section can be on in one language and
  off in the other without a second menu.
- Sections: `[menu.main.params] showInNav = false` keeps a section on the page
  and takes only its link out of the nav, and `[params.sections] order = [...]`
  is the escape hatch for a site that wants the nav and the page in different
  orders on purpose. Order resolves as `params.sections.order`, then the menu,
  then the previous default.
- Sections: **no configuration can fail a build.** Every misconfiguration warns
  and falls back — an unknown section name, a duplicate, an `order` that is not a
  list or is empty, `params.sections` or `[params.<section>]` written as
  something other than a table, and `enable` or `showInNav` set to something that
  is not a boolean (`enable = "false"` is a string, and used to be read as "on"
  in silence). A menu entry whose `url` is the wrong anchor for the section it
  names — `url = "#sobre"` on `identifier = "about"` — warns and has its link
  pointed at the right anchor, because the section's id is fixed by the theme and
  the typo has exactly one possible fix. One naming a section but linking
  somewhere else entirely (a page, an external URL) warns and is left alone: that
  may well be a real destination.
- Sections: the theme warns when a section has content configured, is not turned
  off, and nothing in the index renders it — naming the section and the two ways
  to resolve it. This is the shape of a `[[menu.main]]` written for v0.3.0, where
  the menu drove only the nav: such a menu can now leave a home page with no
  sections at all, and this warning is what keeps that from happening quietly.
  `[params.<section>] enable = false` states that the omission is deliberate and
  silences it; so does deleting the section's params.

### Fixed
- Sections: a site that fills nothing in no longer ships links to sections that
  are not there. Each section decided to exist a different way — `projects`
  behind a `with`, `experience` behind `enable`, `about` and `contact` behind
  nothing at all — so an unconfigured site rendered `about` and `contact` as
  empty shells (heading, rule, nothing) while the nav offered `#projects` and
  `#experience`, two anchors that scrolled nowhere and announced normally to a
  screen reader. A fourth dead link, the hero's own "view projects" button, went
  the same way. All four now answer to one resolution, and CI walks every page of
  every build asserting that no link points at an anchor that is not on the page
  it targets — run against the previous release's bare output, that check reports
  17 dead anchors.
- Sections: `section--last` follows the last section that actually renders. It
  was hardcoded onto `contact`, which was only correct while contact was
  guaranteed to be last; with contact removed or reordered, the page lost the
  96px of breathing room at its end.
- Nav: a site with no links and one language no longer ships a hamburger button
  and an empty mobile menu for it to open.
- Release: the branch cleanup no longer reports failure for a branch that is
  already gone. GitHub answers a delete of an absent ref with 422 "Reference
  does not exist", not 404, and only 404 was mapped to the already-gone case —
  so every release on a repo that deletes the head branch on merge printed
  "remove it by hand" for a branch the merge had already removed. `v0.3.0` did.
  Nothing ever accumulated on the remote — the merge had done the work; only
  the report was wrong. The allowance is scoped to the caller that asks for it,
  so an unexplained 422 stays fatal everywhere else.

### Changed
- Sections: **the menu now moves and removes the sections.** A site that adopted
  `[[menu.main]]` in v0.3.0 — where the menu drove only the nav, and the README
  said so — will see its sections move on upgrade if its nav order differs from
  the layout order, and **lose any section the menu does not name**. A menu
  written for the nav alone, listing say `about` and an external link, now leaves
  the home page with one section instead of four; one naming no section at all
  leaves it with none. Both cases warn, naming each section that went missing.
  Set `[params.sections] order = [...]` to pin the previous layout and section
  set; the nav keeps following the menu.
- Sections: the four section partials (`about`, `projects`, `experience`,
  `contact`) now expect a context of `dict "last" <bool>` and no longer decide
  for themselves whether to render — `sections.html` does. A site that overrode
  `layouts/index.html` and calls them with the page (`{{ partial "about.html" . }}`)
  has to pass the dict instead, or read the plan the way the theme's own
  `index.html` does.
- Experience: the section is now opt-out like the other three, where it used to
  be opt-in. `[params.experience] enable` was the only switch of its kind in the
  theme, and making all four consistent meant picking one default for all of
  them; a section that has `items` filled in and no explicit `enable` now
  renders rather than staying hidden. If that is your config and you want it
  hidden, set `enable = false`. Sites that already set `enable = true` — the
  exampleSite among them — are unaffected: their minified output is byte-identical.

## [0.3.0] — 2026-08-13

### Added
- Hero: the terminal lists the newest posts as a fourth command, `ls ~/blog --latest`,
  with each filename linking to its post. The home page gave no sign a blog existed
  unless you read the nav; this surfaces it without adding a section or touching the
  order of the existing ones. It appears on its own once a language has posts, and
  the names are built from post titles so they follow the reader's language rather
  than the file on disk — `post.md` and `post.pt.md` would otherwise both read as
  English. Ordered by date newest-first regardless of `weight`. Each post's title is
  the link's accessible name. `params.hero.latestPosts` sets how many (`0` disables),
  per site or per language, and `prefers-reduced-motion` gets the links immediately.
- Nav: the menu order is configurable through Hugo's native `[[menu.main]]`, sorted by
  `weight`, instead of being hardcoded in the partial. Labels are translated from each
  entry's `identifier`, so **one block serves every language** — an explicit `name` wins
  when you want a literal label. Anchors resolve against the current language's home, so
  they keep working from inside a blog post, and `pageRef` keeps internal links on the
  right language. Sites without `[[menu.main]]` render exactly as before: the default
  order is the fallback, and the minified output is byte-identical. The blog entry stays
  conditional on the language having posts, `params.navbar.showBlog` still overrides, and
  desktop and mobile now render from a single partial so they cannot drift apart.

### Changed
- Blog cards: the `~/blog/….md` label follows the reader's language. It came from
  the file on disk, and `post.md` and `post.pt.md` collapse to one name, so every
  language showed the English one. It is built from the post title now, sharing
  `partials/post-filename.html` with the hero listing so the two cannot disagree.
  A long name is ellipsized rather than wrapping into the reading time.
- Release: `scripts/release.py` now deletes the `release/vX.Y.Z` branch from the
  remote once the tag is pushed. It already removed the local copy, so the remote
  one accumulated — one orphan per release, as `v0.2.3` left behind. The cleanup
  runs after the release is complete and only reports if it fails, since a
  leftover branch is litter rather than a broken release.

## [0.2.3] — 2026-08-12

### Added
- Release automation: `scripts/release.py` cuts a release end to end (changelog
  promotion, release PR, CI gate, merge, annotated tag), and a `release.yml`
  workflow publishes the GitHub Release from the changelog section on tag push.
  A tag and a GitHub Release are separate objects and the sidebar reads the
  Release — `v0.1.0` and `v0.2.2` were both tagged without one. `RELEASING.md`
  documents the process, including recovery when a step fails.
- Tests: `scripts/test_release.py` covers the logic that decides what gets
  published — changelog promotion, note extraction, tag ordering, token scoping
  and the CI gate — against the real `CHANGELOG.md`. `ci.yml` runs it on every
  pull request, so a release PR validates its own promoted changelog before it
  can merge. Tooling that merges to `main` and pushes tags should not be the
  one part of the repository nothing checks.

### Changed
- Docs: `images/screenshot.png` and `images/tn.png` are now captures of the bundled
  `exampleSite/` — what the demo and the theme gallery actually serve — instead of a
  personal site with unrelated branding and content. Both were also recaptured without
  the browser scrollbar that had been baked into them, and the README image now uses a
  relative path so it resolves outside github.com too.

## [0.2.2] — 2026-08-11

### Added
- CI: a `ci.yml` workflow builds every pull request, which nothing did before.
  It builds the bundled `exampleSite/` **and** a bare site with no params — the
  path a fresh consumer takes, which the `exampleSite` never exercises — against
  both the `min_version` declared in `theme.toml` (0.158.0) and the version
  `pages.yml` deploys with. Warnings are fatal, missing translations included.
  Kept separate from `pages.yml` — a PR check needs none of the Pages machinery.

### Fixed
- Mobile: the section heading no longer wraps mid-title. On viewports ≤760px the
  `.muted-note` annotation (e.g. "— 03 featured repositories") now takes its own line
  instead of competing with the `<h2>` for horizontal space, which pushed
  "// projects" onto two lines and collapsed the rule to 0px.

## [0.2.1] — 2026-06-21

### Changed
- Docs: updated the theme-submission instructions (PR to `gohugoio/hugoThemesSiteBuilder`,
  adding the repo to `themes.txt`) and added a GitHub Pages workflow that publishes the
  `exampleSite/` demo.

### Fixed
- Home and in-page anchor links (nav brand/links, 404) now respect a baseURL sub-path, so
  the nav works on project sites served under a path (e.g. `…/terminal-mono/`).
- The home page builds without portfolio params: the hero tech-stack and the projects
  section are guarded, so the theme renders against generic content (e.g. a fresh site)
  instead of erroring on empty `about.skills` / `projects`.

## [0.2.0] — 2026-06-21

### Added
- `params.navbar.showBlog` (optional, `true`/`false`) to force the navbar blog link on
  or off, overriding the automatic detection.
- Theme credit in the footer, next to the Hugo link (“made with Hugo & terminal-mono”).

### Changed
- The navbar blog link (desktop and mobile) now appears only when the current language
  has at least one published post, instead of always pointing to an empty `/blogs/`. In
  multilingual sites it shows per language.
- Moved the last hardcoded UI labels to i18n (the `email` link label, the social-link
  fallback, and the 404 “no such file or directory” line), so a site in any language is
  fully localized. New keys: `email`, `nf_no_such_file`.

### Fixed
- The experience timeline no longer renders an empty `<div class="tl-date">` for jobs
  without a `date`.

## [0.1.0] — 2026-06-20

### Added
- Initial release of **Terminal Mono**: a dark/monospace theme for portfolio + blog.
- Home (portfolio) with an animated terminal hero, repository-style project cards,
  about/skills, experience and contact sections.
- Full blog: paginated list, post with a table of contents, tag pages and sharing.
- Terminal-styled 404 page.
- Hugo asset pipeline (minify + fingerprint + SRI in production).
- SEO: Open Graph, Twitter Card, JSON-LD, RSS and `canonical`.
- Accessibility: "skip to content" link, visible focus and `prefers-reduced-motion`.
- Markdown render hooks (headings, images and links) and syntax highlighting (Chroma).
- Internationalization (Hugo i18n) with English (default) and Portuguese, a language
  switcher, `hreflang` alternates and locale-aware dates.
- Complete bilingual `exampleSite/` and Hugo Modules support.

[Unreleased]: https://github.com/adamsalves/terminal-mono/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/adamsalves/terminal-mono/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/adamsalves/terminal-mono/compare/v0.2.3...v0.3.0
[0.2.3]: https://github.com/adamsalves/terminal-mono/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/adamsalves/terminal-mono/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/adamsalves/terminal-mono/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/adamsalves/terminal-mono/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/adamsalves/terminal-mono/releases/tag/v0.1.0
