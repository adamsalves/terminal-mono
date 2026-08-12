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
- 🌍 Multilingual via Hugo i18n — **English + Portuguese** included, with a language switcher and localized dates.

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
  i18n/                      # en.toml (default), pt.toml
  static/favicon.svg
  archetypes/                # default.md, blogs.md
  exampleSite/               # bilingual demo site + commented config
```

## Content (all via `params`)

| Section | Params |
|---|---|
| Brand/nav | `params.title`, `params.navbar.brandName`, `params.navbar.showBlog` (optional), `params.terminalUser`; order via [`[[menu.main]]`](#nav-menu-order) (optional) |
| Hero | `params.hero.intro/subtitle/location/content`, `params.hero.socialLinks.fontAwesomeIcons[]` |
| Hero — terminal | builds "whoami / cat stack.txt / ls projects/" from `title`, `subtitle`, skills and projects; adds [`ls ~/blog --latest`](#latest-posts-in-the-hero-terminal) when the language has posts — `params.hero.latestPosts` (optional, default 3) |
| Projects | `params.projects.items[]` → `title`, `repo`, `language`, `tagline`, `content`, `badges[]`, `featured{name,link}`, `links[]{icon,url,name}` |
| About + skills | `params.about.content` (markdown), `params.about.skills.enable/items[]` |
| Experience | `params.experience.enable`, `params.experience.items[]` → `company`, `jobs[]{name, date (optional), content}` |
| Contact | `params.contact.title/content/btnName/btnLink` |
| Footer | `params.footer.copyright`, `params.footer.socialNetworks.github/linkedin` |
| Blog | `content/blogs/*.md` → `title`, `date`, `tags`, `description`, `image` (optional), `toc` |

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
name for screen readers.

`params.hero.latestPosts` sets how many to show (default `3`); `0` drops the
command entirely. Set it under `[params.hero]` for the whole site, or under
`[languages.<lang>.params.hero]` to vary it per language.

Links become clickable as each name finishes typing. Readers with
`prefers-reduced-motion` get the whole terminal, links included, immediately.

### Nav menu order

The nav renders `about, projects, experience, blog, contact` by default. Define
`[[menu.main]]` to choose the order yourself — Hugo's native menu, sorted by
`weight`:

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
  pageRef = "/blogs"    # pageRef, not url — see below
  weight = 30
```

Omit the block entirely and nothing changes: the default order is the fallback,
so an existing site upgrades without touching its config.

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

Menu order and the order the home page renders its sections are independent:
this controls the nav only.

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

UI strings live in `i18n/en.toml` (the default / fallback) and `i18n/pt.toml`. The
bundled `exampleSite` is bilingual — **English at `/`, Portuguese at `/pt/`** — and shows
a language switcher in the nav (rendered automatically when the site has more than one
language). Missing keys fall back to `defaultContentLanguage`; dates are localized from
each language's `locale`.

To add a language (e.g. Spanish):

1. Copy `i18n/en.toml` to `i18n/es.toml` and translate the values.
2. Declare the language and translate its content params:
   ```toml
   [languages.es]
     label = "Español"
     locale = "es-ES"
     weight = 3
     [languages.es.params]
       # title, description, hero, about, experience, projects, contact …
   ```
3. Translate posts with the filename convention: `my-post.es.md`.

> Single-language sites work too: just keep one `[languages.*]` (or none) — the switcher
> hides itself and the lone i18n table drives every string.

## Customization

- **Colors and fonts:** CSS variables in the `:root` of `assets/css/terminal.css`
  (e.g. change the accent by editing `--accent`).
- **Global toggles:** `params.showScanlines` (CRT overlay) and `params.readingProgress`.
- **`partials/extend-head.html`** and **`partials/extend-footer.html`** (at the project
  level) are injected into `<head>` and before `</body>` — handy for analytics or
  comments without touching the theme.
- **Syntax highlighting:** the Chroma colors live at the end of `terminal.css`
  (`noClasses = false` in config). Tweak them freely.

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
