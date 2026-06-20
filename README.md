# Terminal Mono — Hugo theme

Personal **dark / monospace** theme for portfolio + blog. Typing terminal hero, repository-style project cards, a blog with a reading-progress bar, tag pages and a 404 — all in the same aesthetic. **No third-party JS dependencies.**

![Terminal Mono](images/screenshot.png)

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
| Brand/nav | `params.title`, `params.navbar.brandName`, `params.terminalUser` |
| Hero | `params.hero.intro/subtitle/location/content`, `params.hero.socialLinks.fontAwesomeIcons[]` |
| Hero — terminal | builds "whoami / cat stack.txt / ls projects/" from `title`, `subtitle`, skills and projects |
| Projects | `params.projects.items[]` → `title`, `repo`, `language`, `tagline`, `content`, `badges[]`, `featured{name,link}`, `links[]{icon,url,name}` |
| About + skills | `params.about.content` (markdown), `params.about.skills.enable/items[]` |
| Experience | `params.experience.enable`, `params.experience.items[]` → `company`, `jobs[]{name,date,content}` |
| Contact | `params.contact.title/content/btnName/btnLink` |
| Footer | `params.footer.copyright`, `params.footer.socialNetworks.github/linkedin` |
| Blog | `content/blogs/*.md` → `title`, `date`, `tags`, `description`, `image` (optional), `toc` |

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
2. **Tag a version** (SemVer) — this is what Hugo Modules and the submodule use:
   ```bash
   git tag -a v0.1.0 -m "Terminal Mono v0.1.0"
   git push origin v0.1.0
   ```
3. (Optional) **Live demo:** `netlify.toml` already builds the `exampleSite/`. Connect the
   repo on Netlify and update `homepage`/`demosite` in `theme.toml`.
4. (Optional) **Official gallery:** submit the theme to
   [themes.gohugo.io](https://github.com/gohugoio/hugoThemesSiteBuilder) — the requirements
   (`theme.toml`, `LICENSE`, `exampleSite/`, `images/screenshot.png` + `images/tn.png`)
   are already met.

> When you move the repository, update the `module` in `go.mod`, the `licenselink` in
> `theme.toml`, and the links in `CHANGELOG.md`/`README.md` to the new path.

---

Built for **adamsalves.dev**. MIT license.
