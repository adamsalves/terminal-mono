# Terminal Mono — Hugo theme

Personal **dark / monospace** theme for portfolio + blog. Typing terminal hero, repository-style project cards, a blog with a reading-progress bar, tag pages and a 404 — all in the same aesthetic. **No third-party JS dependencies.**

![Terminal Mono](images/screenshot.png)

**[Live demo →](https://adamsalves.github.io/terminal-mono/)** — the screenshot above is
the bundled `exampleSite/`, which is exactly what the demo serves.

- 🎨 Dark-only, JetBrains Mono, lime accent — all driven by CSS variables.
- ⌨️ Hero terminal with a typewriter effect (degrades gracefully without JS).
- 🗂️ Portfolio content 100% from `params` — no template editing.
- ✍️ Full blog: paginated list, post with TOC, tag pages and sharing.
- ⚡ Hugo asset pipeline (minify + fingerprint + SRI in production).
- 🔎 SEO ready: Open Graph, Twitter Card, JSON-LD, RSS and `canonical`.
- ♿ Accessible: "skip to content" link, visible focus and `prefers-reduced-motion`.
- 🌍 Multilingual via Hugo i18n — **English + Portuguese** included, with a language switcher and localized dates. Any other language falls back to English rather than rendering blank labels.

Requires **Hugo extended ≥ 0.158**.

## Preview (exampleSite)

The theme ships with a ready-to-run example site:

```bash
cd exampleSite
hugo server --themesDir ../..
```

Open <http://localhost:1313>. The `exampleSite/hugo.toml` documents **every** available `param`.

## Installation

### Via Hugo Modules (recommended)

```bash
hugo mod init github.com/your-name/your-site   # if you don't use modules yet
hugo mod get github.com/adamsalves/terminal-mono
```

```toml
# hugo.toml
[module]
  [[module.imports]]
    path = "github.com/adamsalves/terminal-mono"
```

### Via Git submodule

```bash
git submodule add https://github.com/adamsalves/terminal-mono themes/terminal-mono
```

```toml
# hugo.toml
theme = "terminal-mono"
```

### Manual copy

Copy the folder into `themes/terminal-mono/` and set `theme = "terminal-mono"` in your config.

## Structure

```
terminal-mono/
  theme.toml                 # theme metadata
  hugo.toml                  # theme config: the module mounts (see Languages)
  assets/
    css/terminal.css         # styles (pipeline: minify + fingerprint)
    js/terminal.js           # menu, progress bar, typewriter
  layouts/
    index.html               # home (portfolio)
    404.html
    _default/
      baseof.html  list.html  single.html  term.html  terms.html
      _markup/                # render hooks (heading, image, link)
    partials/
      head.html  nav.html  footer.html  lang-switch.html
      hero.html  projects.html  about.html  experience.html  contact.html
      post-card.html  pager.html
  i18n/                      # en.toml (default + fallback for every language), pt.toml
  static/                    # favicon.svg + one per palette (amber, cyberpunk, ice, mono)
  archetypes/                # default.md, blogs.md
  exampleSite/               # bilingual demo site + commented config
```

## Content (all via `params`)

| Section | Params |
|---|---|
| Brand/nav | `params.title`, `params.navbar.brandName`, `params.navbar.showBlog` (optional), `params.terminalUser`; the nav links **and** the section order come from [`[[menu.main]]`](#the-menu-and-the-sections) (optional) |
| Hero | `params.hero.intro/subtitle/location/content`, `params.hero.socialLinks.fontAwesomeIcons[]` |
| Hero — terminal | builds "whoami / cat stack.txt / ls projects/" from `title`, `subtitle`, skills and projects; adds [`ls ~/blog --latest`](#latest-posts-in-the-hero-terminal) when the language has posts — `params.hero.latestPosts` (optional, default 3). Each command follows the section that owns its data, so a command with nothing to print is not typed at all — `whoami` excepted, which always runs: `cat stack.txt` needs `about` to render **and** `skills.enable = true`, `ls projects/` needs `projects` to render (see [the menu and the sections](#the-menu-and-the-sections)) |
| Projects | `params.projects.items[]` → `title`, `repo`, `language`, `tagline`, `content`, `badges[]`, `featured{name,link}`, `links[]{icon,url,name}`; `params.projects.enable` (optional) |
| About + skills | `params.about.content` (markdown), `params.about.skills.items[]` gated by `params.about.skills.enable` (required — an absent key counts as off, and silences the hero's `cat stack.txt` with the block); `params.about.enable` (optional — the section, not the skills block) |
| Experience | `params.experience.items[]` → `company`, `jobs[]{name, date (optional), content}`; `params.experience.enable` (optional) |
| Contact | `params.contact.title/content/btnName/btnLink`; `params.contact.enable` (optional) |
| Footer | `params.footer.copyright`, `params.footer.socialNetworks.github/linkedin` |
| Blog | `content/blogs/*.md` → `title`, `date`, `tags`, `description`, `image` (optional), `toc` |
| Colors | `params.theme.palette` (optional, default `lime`) and `params.theme.colors.*` (optional) — see [Colors](#colors) |

### Latest posts in the hero terminal

Once a language has published posts, the hero terminal types a fourth command
and lists the newest ones:

```
robin@portfolio:~$ ls ~/blog --latest
2026-03-12  migrating-trailhead-to-nuxt-3.md
2026-02-27  a-chiptune-with-the-web-audio-api.md
2026-02-08  planning-poker-with-socket-io.md
```

Each filename is a link to the post. There is nothing to switch on — the listing
appears when posts exist and disappears when they don't. Posts are ordered by
date, newest first, regardless of any `weight` you set.

**The names follow the reader's language.** They are built from each post's
title, not from its file on disk — `post.md` and `post.pt.md` share a filename,
so a Portuguese reader would otherwise get an English listing. Accents are kept
(`programação-e-café.md`), and the post's real title is the link's accessible
name for screen readers. The `~/blog/….md` label on the blog cards is built the
same way, from the same partial, so the two can never disagree; in the terminal
the name is shortened to keep the listing in one column.

`params.hero.latestPosts` sets how many to show (default `3`); `0` drops the
command entirely. Set it under `[params.hero]` for the whole site, or under
`[languages.<lang>.params.hero]` to vary it per language.

Links become clickable as each name finishes typing. Readers with
`prefers-reduced-motion` get the whole terminal, links included, immediately.

### The menu and the sections

`[[menu.main]]` is the page's index. It sets the order of the nav links **and**
the order the home page renders its sections in — one list, so the two can never
disagree about what the page contains.

A section renders when all three of these say yes:

| Gate | Where it lives | A section loses it when |
|---|---|---|
| The switch | `[params.<section>] enable` | you set it to `false` |
| The index | `[[menu.main]]` (or `params.sections.order`) | its block is not there |
| The content | the section's own params | you filled nothing in |

The four sections are `about`, `projects`, `experience` and `contact`. The hero
is the page's header rather than a section: always first, not movable, not
removable. Any other identifier — `blog`, an external link — is nav-only.

"Content of its own" means:

| Section | Has content when |
|---|---|
| `about` | `content` is set, or `skills.enable` with a non-empty `skills.items` |
| `projects` | `items` is not empty |
| `experience` | `items` is not empty |
| `contact` | any of `title`, `content`, `btnLink` |

The built-in translations dress a section; they do not justify one. So a site
that fills nothing in gets no sections — and no links pointing at them, which is
the whole point: a link to a section that does not render is a dead link.

#### 1. Order — the nav and the page, together

Hugo's native menu, sorted by `weight`:

```toml
[[menu.main]]
  identifier = "projects"
  url = "#projects"     # anchors resolve against the language's home
  weight = 10
[[menu.main]]
  identifier = "about"
  url = "#about"
  weight = 20
[[menu.main]]
  identifier = "blog"
  pageRef = "/blogs"    # nav-only: the blog is not a section
  weight = 30
[[menu.main]]
  identifier = "contact"
  url = "#contact"
  weight = 40
```

The home page now renders `projects`, `about`, `contact` in that order, and the
nav lists them with the blog in between.

Omit `[[menu.main]]` entirely and nothing changes from before this feature
existed: the nav falls back to `about, projects, experience, blog, contact` and
the page to `projects, about, experience, contact`. The two defaults are not the
same list, and they stay that way — defining a menu is what makes them agree.

#### 2. Remove a section

Delete its menu block. The section and its nav link both go.

If you also delete `[params.<section>]`, that is the whole story. If you leave
the section's content in the config, the theme warns that it is carrying content
nothing renders — see [§3](#3-turn-a-section-off-without-touching-the-menu) for
how to say the omission is deliberate. That warning is what stops a menu written
before this feature existed from silently emptying a home page.

#### 3. Turn a section off without touching the menu

```toml
[params.experience]
  enable = false
```

Same result, and the section's config stays where it is for the day you want it
back. Use whichever says what you mean: **delete the block** when the section is
not part of this site, **`enable = false`** when it is, just not right now.

`enable = false` is also how you keep a section's content in the config while
leaving it out of the menu without being warned about it every build: it is the
config saying "yes, I meant to leave this out".

`enable` is a veto, never a summons. `false` removes the section whatever the
menu says; `true` grants nothing the index and the content do not already grant,
so it cannot pull back a section you deleted from the menu or one you never
filled in. It is an ordinary param, so
`[languages.pt.params.experience] enable = true` turns a section on for one
language while it stays off in the other.

#### 4. Keep a section, drop its nav link

```toml
[[menu.main]]
  identifier = "about"
  url = "#about"
  weight = 20
  [menu.main.params]
    showInNav = false
```

The section still renders in its menu position; only the link is gone.

#### 5. Menus per language

Menus are language-scoped in Hugo, so a site that wants different sections in
each language defines `[languages.<lang>.menu.main]`. Labels resolve from the
`identifier` either way (see below), so a single shared menu is usually enough.

#### 6. Escape hatch — nav and page in different orders on purpose

```toml
[params.sections]
  order = ["about", "projects", "experience", "contact"]
```

This beats the menu for the page while the nav keeps following the menu. It is
also the migration path if you adopted `[[menu.main]]` in v0.3.0 with a nav order
that differs from the layout: pin the old section order here and nothing moves.

It still drops nav links to sections that do not render — gate three outranks it,
because a dead link is not a layout choice.

#### When the config is wrong

The theme warns and falls back. **None of it can fail your build** — that is the
rule the list below exists to keep:

| What | What the theme does |
|---|---|
| `params.sections` written as anything but a table | warns, ignores it |
| `order` that is not a list, or is empty | warns, ignores it |
| `order` naming an unknown section, or naming one twice | warns, ignores the whole list |
| `enable` or `showInNav` set to something that is not `true`/`false` | warns, ignores it |
| `[params.<section>]` written as a scalar instead of a table | warns, treats the section as unconfigured |
| a menu entry whose `url` is the wrong anchor (`#sobre` for `about`) | warns, points the link at the right one |
| a menu entry naming a section but linking elsewhere (a page, an external URL) | warns, leaves the link alone — it may be a real page |
| content configured for a section nothing renders | warns, naming the section and how to silence it |


**Labels are translated from `identifier`.** One block serves every language —
`identifier = "about"` renders "about" in English and "sobre" in Portuguese,
with no need to repeat the menu per language. The precedence is:

1. **`name`**, if you set one — an explicit label wins and is never translated.
2. **`i18n` of the `identifier`**, when the theme (or your own `i18n/` files) has that key.
3. **The `identifier` itself**, so a link is never blank.

Add your own keys to `i18n/<lang>.toml` to translate a custom entry, or give it
a `name` if a single literal label is enough. Give every entry an `identifier`
or a `name` — one with neither has no label to render, and is skipped rather
than emitted as an empty link.

One caveat on rule 1: an entry with `pageRef` inherits `name` from the target
page's title when you leave it unset, and Hugo exposes no way to tell the two
apart. So a `name` that is *identical* to that title is read as inherited, and a
translation of the `identifier` wins instead. It only bites when both collide —
`identifier = "blog"` plus `name = "Blogs"` pointing at a section titled
"Blogs". Rename either side, or use `url` instead of `pageRef`, to get the
literal label.

**Use `pageRef` for internal pages, not `url`.** `pageRef = "/blogs"` resolves
per language (`/pt/blogs/` in Portuguese); `url = "/blogs/"` would point every
language at the English section. Anchors (`#about`) and external links are
written as `url`.

**The blog entry stays conditional.** An entry with `identifier = "blog"` still
follows the automatic rule below — ordering it by weight does not turn it into a
permanent link to an empty section.

**The nav is a single row, so submenus are not rendered.** An entry with a
`parent` is dropped — the theme has no dropdown to put it in. Keep every entry
at the top level.

### Project colors

The "language dot" on each card is colored automatically from `language`
(or the first `badge`): Vue/Nuxt, TypeScript, React, Phaser, Svelte, Node and Java
ship with their own color. The `~/...` path comes from `repo` (or the slugified title).

## Blog

```bash
hugo new blogs/my-post.md
```

- `description` in the front matter becomes the card summary and the meta description.
- `image` becomes the post banner; without it, we use the styled `~/blog/<slug>.md` banner.
- `toc: true` forces the table of contents (by default it appears on long posts). `toc: false` disables it.
- Tags generate the `/tags/` and `/tags/<tag>/` pages.
- The navbar **blog link appears automatically** once a language has at least one post
  (and hides when it has none). Override with `params.navbar.showBlog = true/false`.

## Languages (i18n)

UI strings live in `i18n/en.toml` and `i18n/pt.toml`. The bundled `exampleSite` is
bilingual — **English at `/`, Portuguese at `/pt/`** — and shows a language switcher in
the nav, rendered automatically when the site has more than one language.

**Adding a language is configuration. Translating the interface is one file.** They are
separate steps, and it is worth knowing which is which:

1. Declare the language and translate its content params:

   ```toml
   [languages.es]
     label  = "Español"   # `languageName` is the pre-0.158 spelling, now deprecated
     locale = "es-ES"     # likewise `languageCode`; sets <html lang> and og:locale
     weight = 3
     [languages.es.params]
       # title, description, hero, about, experience, projects, contact …
   ```

   Everything the theme does per language follows from that, with nothing else to write:
   the switcher, `hreflang`, `og:locale:alternate`, the menu, and post dates — which are
   localized from the language key itself, so `[languages.es]` prints `14 mar 2026`
   whether or not `locale` is set.

2. Translate posts with the filename convention: `my-post.es.md`.

3. Copy `i18n/en.toml` to `i18n/es.toml` **in your own site** and translate the values.
   Hugo merges your `i18n/` over the theme's key by key, so this never requires vendoring
   or forking the theme.

**A language with no strings file renders in English, and says so.** Hugo's fallback for
a missing key is the site's `defaultContentLanguage`, not the theme's `i18n/en.toml` — so
a Spanish-default site without `i18n/es.toml` rendered every label as the empty string:
`// ` for the hero intro, `[  ]` for the contact button, nav links with no text, on a
green build with no warning. The theme now puts its own English table underneath every
lookup and warns once per language:

```
WARN  terminal-mono: no UI strings for language "es" — the interface is falling back to
English. Copy the theme's i18n/en.toml to i18n/es.toml in your site and translate it.
```

That covers every language, not just the default one. The count comes from reading the
translation files rather than from asking Hugo for each value, because a value cannot
tell you where it came from: in a language Hugo has already substituted the default
language's string for, `i18n "about"` returns the English, so `[languages.es]` with no
`i18n/es.toml` — step 3 skipped, exactly the site this section tells you how to build —
used to warn about nothing at all.

A partially translated file gets the other half of that message — how many strings are
missing, and which ones, named up to twelve at a time. A key written as `other = ""`
counts as missing: a blank label is the failure the warning exists to make visible.

Your own `i18n/en.toml` is merged over the theme's, key by key, the same way the
translation lookup itself merges — so a site that renames `projects` to `work` in English
gets `work` in the languages falling back to English too, and the strings it did not
override keep coming from the theme. If that file cannot be parsed, the build says so and
keeps the theme's English rather than failing.

> Single-language sites work too: keep one `[languages.*]`, or none — the switcher hides
> itself and the lone table drives every string.
>
> **Left-to-right only.** `languageDirection = "rtl"` does reach the page as
> `<html dir="rtl">`, but `terminal.css` is written with physical `left`/`right`
> properties and does not mirror. RTL is untested and unclaimed.

## Colors

The theme ships five palettes. Pick one in the config — there is nothing to edit in
the theme, which matters because a theme pulled in as a Hugo Module or a submodule is
not yours to edit:

```toml
# hugo.toml
[params.theme]
  palette = "cyberpunk"   # lime (default) · amber · cyberpunk · ice · mono
```

| Palette | Accent | |
|---|---|---|
| `lime` | `#b6ff3c` | Green phosphor. The default, and what every earlier version rendered. |
| `amber` | `#ffb000` | The other CRT phosphor. The ground goes warm with it. |
| `cyberpunk` | `#ff2fd0` + `#3fb9cf` | Neon magenta with cyan prompts, on violet-black. |
| `ice` | `#4fd6ff` | Cold cyan on slate. Reads as an editor rather than a CRT. |
| `mono` | `#ffffff` | No hue at all — white phosphor on true black. |

The choice is made at build time and the published site has one palette. This is not a
light/dark toggle: the theme is [dark-only by design](#notes), and all five are dark.

An unknown name warns and falls back to `lime` rather than failing the build.

Palette colors are mixed with [`color-mix()`](https://caniuse.com/mdn-css_types_color_color-mix)
(Chrome 111, Safari 16.2, Firefox 113 — all 2023). Older browsers keep the nav, the mobile
menu and the code-block borders through a literal fallback, and lose only decorative
glows and hover tints.

### Overriding individual colors

`[params.theme.colors]` is applied on top of the palette, so you can start from one and
change only what you want:

```toml
[params.theme]
  palette = "cyberpunk"

  [params.theme.colors]
    accent    = "#00ffd5"
    accentDim = "#ff2fd0"
```

Any of these keys, each mapping to the CSS custom property of the same name in
kebab-case (`surface2` → `--surface-2`, `accentDim` → `--accent-dim`):

| | |
|---|---|
| **Ground** | `bg` · `surface` · `surface2` · `surface3` |
| **Lines** | `border` · `borderSoft` · `borderFaint` |
| **Text** | `text` · `soft` · `prose` · `muted` · `muted2` · `dim` · `dim2` |
| **Accent** | `accent` · `accentDim` · `danger` |
| **Code** | `codeKey` · `codeType` · `codeStr` · `codeNum` |

Case and punctuation are yours: `accentDim`, `accentdim`, `accent-dim` and `accent_dim`
are the same key, so the spelling you copied out of the stylesheet works too.

Values are hex codes or CSS color functions (`oklch(70% 0.2 150)`, `rgb(0 0 0 / 40%)`),
written as quoted strings. A key that isn't on this list, or a value that isn't a color —
a bare number, an unquoted `true`, a function with its parenthesis left open — is ignored
with a warning naming it. A typo that silently did nothing would look exactly like a
broken feature.

The rest of the theme follows the palette on its own: button glows, the reading-progress
bar, the hero typewriter, the 404, and the favicon in the browser tab.

### Syntax highlighting

Chroma follows the palette through `codeKey` / `codeType` / `codeStr` / `codeNum`
(comments, function names and diff markers follow the accent instead). `amber` and
`cyberpunk` restate the four; `lime` and `ice` share the blue-and-teal default.

**`mono` renders code in grayscale**, which is the palette's premise rather than an
oversight — but it costs code posts the hue that separates a string from a keyword.
Put it back without giving up the rest of the palette:

```toml
[params.theme]
  palette = "mono"
  [params.theme.colors]
    codeKey = "#7da6ff"
    codeType = "#56b6c2"
    codeStr = "#d7b56d"
    codeNum = "#d19a66"
```

## Customization

- **Fonts:** the `--mono` variable. Set it from your own
  `partials/extend-head.html` (`<style>:root:root{--mono:'IBM Plex Mono',monospace}</style>`)
  rather than by editing `assets/css/terminal.css` — a theme pulled in as a Hugo
  Module or a submodule is not yours to edit. `:root:root` for the same reason
  `[params.theme.colors]` uses it: a plain `:root` loses to a palette block.
- **Global toggles:** `params.showScanlines` (CRT overlay) and `params.readingProgress`.
- **`partials/extend-head.html`** and **`partials/extend-footer.html`** (at the project
  level) are injected into `<head>` and before `</body>` — handy for analytics or
  comments without touching the theme.
- **Project colors:** the language dot on each card comes from the project's own
  `language`, not from the palette — Vue stays Vue green in all five. See
  [Project colors](#project-colors).

## Notes

- **Dark-only by design.** There's no light/dark toggle.
- **No FontAwesome.** The theme uses its own labels/icons.
- **Accessibility:** respects `prefers-reduced-motion` (disables the typewriter and animations).

## Publishing / versioning

The theme is already a self-contained, versionable folder. To distribute it:

1. Create a repository (e.g. `github.com/adamsalves/terminal-mono`) and push the content:
   ```bash
   git push -u origin main
   ```
2. **Cut a version** (SemVer) — this is what Hugo Modules and the submodule use:
   ```bash
   ./scripts/release.py 0.2.3
   ```
   That promotes the changelog, opens and merges the release PR, pushes the annotated
   tag, and publishes the GitHub Release. See **[RELEASING.md](RELEASING.md)** for the
   prerequisites, how to pick the number, and how to recover if a step fails.
3. **Live demo:** a GitHub Actions workflow (`.github/workflows/pages.yml`) builds the
   `exampleSite/` and deploys it to GitHub Pages on every push to `main`
   (<https://adamsalves.github.io/terminal-mono/>). `netlify.toml` is included as an
   alternative.
4. **Official gallery ([themes.gohugo.io](https://themes.gohugo.io)):** submit a **pull
   request** to [`gohugoio/hugoThemesSiteBuilder`](https://github.com/gohugoio/hugoThemesSiteBuilder)
   adding this repo's URL to `themes.txt` (lexicographical order); the Netlify deploy preview
   on the PR must pass. Requirements (all met): `theme.toml`, an OSI `LICENSE`, `README.md`,
   an `exampleSite/` with `baseURL = "https://example.com"`, `images/screenshot.png`
   (1500×1000) and `images/tn.png` (900×600).

> When you move the repository, update the `module` in `go.mod`, the `licenselink` in
> `theme.toml`, and the links in `CHANGELOG.md`/`README.md` to the new path.

---

Built for **adamsalves.dev**. MIT license.
