# Changelog

All notable changes to this theme are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- The palette is configuration. `[params.theme] palette = "…"` picks one of five —
  `lime` (the default, and what every earlier version rendered), `amber`, `cyberpunk`,
  `ice` and `mono` — and `[params.theme.colors]` overrides individual tokens on top of
  whichever won. Until now the README's answer to "change the accent" was to edit
  `--accent` in `assets/css/terminal.css`, which is advice a site can only follow if it
  vendored the theme; consumed as a Hugo Module or a submodule the file is not the
  site's to edit, so the theme was effectively one color. Closes #30.

  Palettes live in the stylesheet as `:root[data-palette="…"]` blocks, stamped onto
  `<html>` by `baseof.html` — `terminal.css` stays static, so it keeps being minified,
  fingerprinted and cached the way it was, and a site that configures nothing gets the
  bare `:root`, which is still lime. Overrides are the one thing that has to come from
  the config, and they arrive as a `<style>` element after the stylesheet. It is written
  `:root:root` on purpose: a palette selector is 0,2,0 and a plain `:root` is 0,1,0, so
  the obvious spelling would have worked on lime and silently done nothing on the other
  four — the harder half of that bug to notice.

  An unknown palette name, a `[params.theme]` written as a scalar, an unknown color key
  and a value that is not a color each warn and are ignored. None of them fails the
  build, which is the rule `sections.html` set and the `params-*.html` guards enforce.

### Fixed
- Colors that did not follow the accent because they never went through it. Eight
  `rgba(182,255,60,…)` washes were spelled out in `terminal.css` — the solid button's
  glow, the reading-progress bar, the contact box, the tag hover, the blockquote, the
  post banner's dot grid, the 404's text-shadow and the gradient behind the whole body —
  along with the typewriter's five colors in `terminal.js`, five inline `style="color:#…"`
  attributes in `404.html`, and the favicon. They were correct while there was one
  palette and would have stayed lime green in the other four. The washes are now
  `color-mix()` against `var(--accent)`; the script and the 404 emit `var(--accent-dim)`
  and friends rather than hex, which also removes the question of when it is safe to
  read a computed color, since nothing is resolved in JavaScript at all; and each palette
  ships its own favicon. The neutral overlays stay literal — the white scanlines and the
  black drop shadows are not palette colors and read the same on every ground.

  Under `lime` every one of these resolves to the value it had before, exactly, with two
  exceptions — both derivations of a value that had been picked by hand, and both under
  2/255 of where they were:

  - the border on code blocks, `#232a1c`, now derived from `--border` and `--border-soft`:
    +1 on red and +2 on blue, on a 1px rule;
  - the post banner's gradient, `#11160d`, now `--surface-2` (`#11140d`): −2 on green.

- Browser chrome follows the palette too: `<meta name="theme-color">` carries the
  palette's ground, or the `[params.theme.colors]` override of it, so an amber site does
  not get a lime address bar drawn around it — the same argument as the per-palette
  favicon, one layer out.

- `color-mix()` has a literal fallback where it reaches something structural. A
  declaration carrying `color-mix()` parses fine and only becomes invalid at
  computed-value time, which resolves to the property's *initial* value rather than to
  an earlier declaration — so the usual two-declaration fallback does not work through a
  custom property, and on a browser without the function (pre-2023) the sticky nav and
  the open mobile menu both went transparent over the scrolling page, and the code-block
  borders disappeared. The derived tokens now carry the values the theme shipped before
  palettes existed and are upgraded inside `@supports`. Decorative mixes — glows, hover
  tints, shadows — are deliberately left to degrade to nothing.

- `[params.theme.colors]` keys accept the spelling you copied out of the stylesheet:
  `accentDim`, `accentdim`, `accent-dim` and `accent_dim` are one key. TOML bare keys
  do permit `-`, so `accent-dim` was reaching the theme intact and being reported as an
  unknown key.

- `[params.theme.colors]` rejects two values it used to emit. A non-string — `accent = true`,
  `accent = 255` — is never a color, and emitted CSS that was valid to parse and invalid
  to compute, so every `var(--accent)` on the page fell back to nothing with no warning.
  A value with an unclosed parenthesis — `accent = "rgb("` — swallowed every declaration
  after it in the block, so one typo silently deleted the *other* overrides. Both now
  warn and are ignored.

- The warning for an unknown palette no longer reports printf's error syntax. `palette = 3`
  arrives as an integer and `%q` on an integer is a rune literal, so it announced that the
  requested palette was `'\x03'`; `palette = true` reported `%!q(bool=true)`.

- An untranslated language rendered a blank interface. Hugo's fallback for a missing
  i18n key is the site's `defaultContentLanguage`, not the theme's `i18n/en.toml`, so a
  site whose default language the theme ships no strings for — `defaultContentLanguage
  = "es"` with no `i18n/es.toml` — rendered every label as the empty string: `// ` for
  the hero intro, `[  ]` for the contact button, nav links with no text, the 404 with no
  message. The build was green and said nothing. A language declared *alongside* `en`
  was never affected, which is why the bilingual exampleSite never showed it.

  Every UI string now goes through `partials/t.html`, which asks Hugo first and the
  theme's own English table second, so the floor is a readable page in the wrong
  language rather than an unreadable one in the right language. The English table is
  read from `i18n/en.toml` through Hugo's union filesystem — the theme's real
  translation file, not a copy of it, whether the theme is vendored, a submodule or a
  Hugo Module. One caveat, documented in the README: a site that ships its own
  `i18n/en.toml` shadows the theme's as the fallback source, because that filesystem
  returns the first match instead of merging the way the translation lookup does.

  `partials/i18n-check.html` warns once per language, naming the file to create when a
  language has no strings at all and listing the missing keys when it has some. The
  count comes from calling `i18n` on every English key rather than from reading the
  language's file, so it reports what Hugo actually resolved — site merged over theme —
  and not what one file happens to contain.

  Strings that interpolate a value keep working through the fallback: `{{ .count }}` and
  friends are substituted literally, which is what the one such string in the theme
  (`posts_tagged`) needs. Nothing in the rendered output changed for a site that has its
  translations — the exampleSite builds byte-identical to v0.5.0.

- README: the language section says which half of adding a language is configuration
  (all of it — switcher, `hreflang`, `og:locale:alternate`, menu and dates follow from
  `[languages.<lang>]`) and which half is a file you write. It also records that `label`
  and `locale` are the current spellings — `languageName` and `languageCode` are
  deprecated as of Hugo 0.158, the theme's own minimum — and that dates localize from
  the language key with or without `locale`. Finally it states what the theme does not
  do: `languageDirection = "rtl"` reaches the page as `<html dir="rtl">`, but the
  stylesheet is written in physical `left`/`right` properties and does not mirror, so
  RTL is untested and unclaimed rather than quietly broken.

## [0.5.0] — 2026-08-21

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
- Hero terminal: the reserved height counts the rows the text takes, not the
  lines it is written in. `--hero-lines` was a count of *logical* lines, and
  `.term__body` wraps — so on a 360px phone five of the exampleSite's fifteen
  lines take two rows each, the box reserved 369px for 480px of text, and it grew
  under the reader line by line as the animation typed: the exact shift the
  reservation exists to prevent, on the viewport where it is scored hardest. Only
  the browser knows the box's width and the font's advance, so `terminal.js` now
  measures both and writes the corrected count back before the first character is
  typed — and again whenever the box changes size or JetBrains Mono arrives under
  `font-display:swap`. Width is counted in terminal cells rather than characters,
  so a full-width glyph costs the two it really takes: a Japanese subtitle would
  otherwise model at half its width and the box would come out short again, which
  is this bug wearing the fix as a disguise. The blinking cursor is counted too —
  it belongs to no line of the script, and the closing prompt is where it comes to
  rest. What the template emits is unchanged and becomes the floor: the number a
  reader gets before the script runs, or without it. Not a regression from the
  entry below: v0.4.0 reserved the identical height by a different route and
  carried the same `pre-wrap`, so this is older than both.
- Hero terminal: the reserved height follows the commands that actually render.
  It was a constant `12` lines plus one per post, which was right only while all
  three commands always rendered; drop one and the box reserved three lines it
  never filled, leaving a block of dead space under the hero — the same class of
  bug as `section--last` sitting on a section that was no longer last. The
  template now counts the lines it is about to emit and passes them as
  `--hero-lines`, replacing the `--hero-posts` variable and the
  `.term__body--posts` class, which are gone. CI recomputes the count from the
  rendered `data-*` attributes and holds the variable to it.
- Config: **a param written as the wrong type no longer takes the build down.**
  `sections.html` has always stated the rule in its header — no configuration
  may fail the build — and normalised the four section tables to keep it. But
  every partial that read `site.Params.<x>` straight bypassed that, so the
  promise held in the one file that made it and nowhere else. Thirteen
  configurations aborted a build: `[params.hero]`, `[params.contact]`,
  `[params.footer]` and `[params.navbar]` written as scalars;
  `[params.footer.socialNetworks]`, `[params.hero.socialLinks]` and
  `[params.about.skills]` the same one level down; `items` written as a scalar
  under `about.skills`, `projects` and `experience`; a `jobs` list inside an
  experience entry; and a list of bare strings where `projects`, `experience` or
  `socialLinks` expect a list of tables. Each now warns, names the param, and
  falls back.
  Four of the thirteen broke **every page**, not the home alone — `head.html`,
  `footer.html` and `nav.html` run site-wide, so a scalar `hero`, `contact`,
  `footer` or `navbar` took the 404 and every blog post with it. `navbar` was
  the sharpest of them: `nav.html` is the file the invariant names, and
  `sections.html` already guarded that same param for its `showBlog` gate, so
  the theme disagreed with itself about `[params.navbar]` in two files.
- Config: three new partials carry that — `params-table.html`,
  `params-list.html` and `params-scalar.html` — and every consumer reads through
  them. A guard on a parent says nothing about its children, so nested tables go
  through the same helper; that is the whole reason six of the thirteen existed.
  Lists are tested for *being* lists rather than for truth: `first` does not
  reject a string, it slices its bytes, so `items = "Go"` would have rendered
  `71 · 111` instead of failing anywhere a consumer could see it. Entries
  dropped from a list are counted in the warning, so a typo that silently
  removes one project from six is reported rather than simply absent — and
  entries are checked in both directions now, so a table written where a bare
  skill belongs is dropped and counted rather than rendering `map[a:1]` into a
  skill chip.
- Config: the mirror direction is covered too — a scalar-shaped param written as
  a table or a list. It fails differently and had to be guarded separately:
  these never reach a `range` or a field lookup, they reach `plainify`,
  `relURL`, `absURL`, `markdownify` or `urlize`, all of which cast to string and
  abort when the cast fails. Eight more configurations, on top of the thirteen
  above: `[params.description]`, `[params.favicon]` and `[params.ogImage]`, read
  in `head.html`, so all three took whole sites down; a post's own `image`, from
  its front matter, in `head.html` for `og:image` and again in `single.html` for
  the featured banner; and the prose fields — `[params.about] content`, a
  project entry's `content` and `title`, and an experience job's `content`.
  The per-entry ones name the entry in the warning, by `repo` or by `title` once
  the title itself has been through the guard, so a list of six says which one.
  A param that is only ever printed is left alone on purpose: `map[a:1]` on the
  page is wrong but does not stop the build, and warning about it would report
  the same mistake twice for the reads that do go through a cast.
- Config: gate 3 type-checks `[params.about] content` for the same reason it
  type-checks the lists — a table there is truthy, so it admitted the section
  and then rendered it as an empty shell.
- Config: a warning about an experience entry with no `company` no longer
  degrades into printf's own error syntax. `%q` on a nil printed the warning as
  `items %!q(<nil>) jobs must be a list`, turning the half that names the broken
  entry into noise. CI now watches the warnings for printf garbage as well as
  the pages, since the log is the only place this one could ever appear.
- Config: gate 3 in `sections.html` now type-checks the list-shaped params as
  well as testing them for emptiness. A scalar `items` is truthy, so it used to
  pass the gate and reach the partial; with the partials guarded the build
  survives, but the section would render with nothing in it — the defect v0.4.0
  closed. The warning has to come from the gate for the same reason: once the
  gate drops the section its partial never runs, so a guard that only warned
  inside the partial would go quiet exactly when the config is wrong.
- SEO: a site that never set `[params.hero] subtitle` no longer publishes
  `<title>Site — %!s(&lt;nil>)</title>`. Go's `printf` has no nil case for
  `%s`, so the missing param was formatted straight into the page — on the home
  page of every site that skipped it, including the bare site CI has been
  building all along. Nothing warned, so `--panicOnWarning` could not see it and
  the build stayed green. The title now falls back to the site name alone. CI
  asserts no built page contains printf's error syntax, across every fixture.
- SEO: `jobTitle` and `description` are omitted from the JSON-LD when unset
  instead of emitted as `null`. `jsonify` renders a nil as valid JSON, so this
  was never the defect above — but `"jobTitle":null` asserts that the person has
  no job title, where saying nothing asserts only that this site left the field
  empty.

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
- Docs: `RELEASING.md` now says what `0.x` does with a breaking change. The
  SemVer table had no row for it, and the `major` row's example read `0.3.0` →
  `1.0.0` — which taken literally made v0.4.0, breaking by the table's own
  definition, a `1.0.0`. It was cut as `0.4.0` deliberately, per
  [SemVer §4](https://semver.org/#spec-item-4): while the theme is `0.x` a
  breaking change goes in the minor, and `1.0.0` is reserved for the deliberate
  statement that the contracts are stable. The `major` row now counts from
  `1.0.0` so it stops implying otherwise. Wording only — the script chooses
  nothing, the number is still yours to pass.

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

[Unreleased]: https://github.com/adamsalves/terminal-mono/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/adamsalves/terminal-mono/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/adamsalves/terminal-mono/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/adamsalves/terminal-mono/compare/v0.2.3...v0.3.0
[0.2.3]: https://github.com/adamsalves/terminal-mono/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/adamsalves/terminal-mono/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/adamsalves/terminal-mono/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/adamsalves/terminal-mono/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/adamsalves/terminal-mono/releases/tag/v0.1.0
