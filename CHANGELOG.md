# Changelog

All notable changes to this theme are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- Docs: corrected the theme-submission instructions (open an issue at `gohugoio/hugoThemes`,
  not a PR) and added a GitHub Pages workflow that publishes the `exampleSite/` demo.

### Fixed
- Home and in-page anchor links (nav brand/links, 404) now respect a baseURL sub-path, so
  the nav works on project sites served under a path (e.g. `…/terminal-mono/`).

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

[Unreleased]: https://github.com/adamsalves/terminal-mono/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/adamsalves/terminal-mono/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/adamsalves/terminal-mono/releases/tag/v0.1.0
