# Changelog

All notable changes to this theme are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Release: the branch cleanup no longer reports failure for a branch that is
  already gone. GitHub answers a delete of an absent ref with 422 "Reference
  does not exist", not 404, and only 404 was mapped to the already-gone case —
  so every release on a repo that deletes the head branch on merge printed
  "remove it by hand" for a branch the merge had already removed. `v0.3.0` did.
  The cleanup itself was never reached, which is why nothing accumulated.

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

[Unreleased]: https://github.com/adamsalves/terminal-mono/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/adamsalves/terminal-mono/compare/v0.2.3...v0.3.0
[0.2.3]: https://github.com/adamsalves/terminal-mono/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/adamsalves/terminal-mono/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/adamsalves/terminal-mono/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/adamsalves/terminal-mono/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/adamsalves/terminal-mono/releases/tag/v0.1.0
