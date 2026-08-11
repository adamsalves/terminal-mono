# Changelog

All notable changes to this theme are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/adamsalves/terminal-mono/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/adamsalves/terminal-mono/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/adamsalves/terminal-mono/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/adamsalves/terminal-mono/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/adamsalves/terminal-mono/releases/tag/v0.1.0
