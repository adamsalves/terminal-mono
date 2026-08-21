/* Exercises assets/js/terminal.js against a stubbed DOM.
 *
 * The Hugo build only proves the server rendered data-posts; everything the
 * reader actually sees in the hero terminal is produced by this file, and a
 * build stays green with the whole listing broken. Run: node scripts/test_terminal_js.js
 *
 * No dependencies — the theme ships no package.json and this keeps it that way.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, '..', 'assets', 'js', 'terminal.js');

/* What the fake layout reports: the width the terminal body lays out at, and the
 * advance of one character in it. Set per run, read by every node's
 * getBoundingClientRect. Both zero is a DOM that lays nothing out — jsdom, a
 * display:none ancestor — which the script has to survive without guessing. */
let metrics = { width: 0, char: 0 };

/* A <pre> stand-in recording what the script builds. innerHTML/insertAdjacentHTML
 * are tracked per node so the test can tell a rebuilt subtree from an appended
 * one — the distinction that decides whether a typed link survives as the same
 * DOM node or is destroyed under the reader's cursor. */
function makeNode(tag) {
  return {
    tagName: tag.toUpperCase(),
    children: [],
    attrs: {},
    _html: '',
    rebuilds: 0,
    appends: 0,
    style: { props: {}, setProperty(k, v) { this.props[k] = v; } },
    set innerHTML(v) { this._html = v; this.rebuilds++; },
    get innerHTML() { return this._html; },
    set textContent(v) { this._html = v; },
    get textContent() { return this._html; },
    setAttribute(k, v) { this.attrs[k] = v; },
    appendChild(c) { this.children.push(c); return c; },
    removeChild(c) { this.children = this.children.filter((n) => n !== c); },
    insertAdjacentHTML(pos, html) { this._html += html; this.appends++; },
    /* The script measures with two nested probes: a block that takes the body's
     * content width, and a run of characters inside it. The block is the one
     * carrying a child; the ruler is the one carrying text. */
    getBoundingClientRect() {
      return { width: this.children.length ? metrics.width : this._html.length * metrics.char };
    },
  };
}

function run(dataset, { reduceMotion = false, runTimers = true, width = 0, char = 0 } = {}) {
  const pre = makeNode('pre');
  pre.dataset = dataset;
  pre.clientWidth = width;
  metrics = { width, char };

  const queue = [];
  const listeners = {};
  global.document = {
    getElementById: (id) => (id === 'hero-term' ? pre : null),
    documentElement: { scrollHeight: 0 },
    createElement: makeNode,
    addEventListener: () => {},
  };
  global.window = {
    matchMedia: () => ({ matches: reduceMotion }),
    addEventListener: (type, fn) => { (listeners[type] = listeners[type] || []).push(fn); },
    scrollY: 0,
    innerHeight: 0,
  };
  global.setTimeout = (fn) => { queue.push(fn); return queue.length; };

  new Function(fs.readFileSync(SRC, 'utf8'))();

  // Drain the typewriter. Each tick enqueues the next one; cap it so a runaway
  // loop fails the test instead of hanging CI.
  let guard = 0;
  while (runTimers && queue.length) {
    if (++guard > 500000) throw new Error('typewriter did not terminate');
    queue.shift()();
  }

  const [done, tail] = pre.children;
  return {
    pre,
    done,
    tail,
    html: (done ? done.innerHTML : '') + (tail ? tail.innerHTML : ''),
    // The height the box reserves, in lines. undefined when the script left the
    // template's own count standing.
    lines: pre.style.props['--hero-lines'],
    // Rotate the phone: a new width — and optionally a new advance, so a test can
    // tell a reservation that was re-measured from one that was left alone.
    resize(w, ch = char) {
      pre.clientWidth = w;
      metrics = { width: w, char: ch };
      (listeners.resize || []).forEach((fn) => fn());
      return pre.style.props['--hero-lines'];
    },
  };
}

const POSTS = [
  { d: '2026-03-12', f: 'migrando-o-trailhead-para-o-nuxt-3.md', t: 'Migrando o Trailhead para o Nuxt 3', u: '/pt/blogs/trailhead-nuxt-3/' },
  { d: '2026-02-27', f: 'programação-e-café.md', t: 'Programação e Café', u: '/pt/blogs/programacao/' },
];
const BASE = { user: 'a@b', name: 'N', role: 'R', loc: 'L', stack: 'S', projects: 'p/' };

const checks = [];
const check = (name, fn) => checks.push([name, fn]);

check('lists one link per post, with the post URL', () => {
  const { html } = run({ ...BASE, posts: JSON.stringify(POSTS) });
  const hrefs = [...html.matchAll(/<a href="([^"]*)"/g)].map((m) => m[1]);
  return hrefs.length === 2 && hrefs[0] === POSTS[0].u && hrefs[1] === POSTS[1].u;
});

check('prints the ls command', () => run({ ...BASE, posts: JSON.stringify(POSTS) }).html.includes('ls ~/blog --latest'));

check('link carries the post title as its accessible name', () => {
  const { html } = run({ ...BASE, posts: JSON.stringify(POSTS) });
  return html.includes('aria-label="Migrando o Trailhead para o Nuxt 3"');
});

check('shows the language-specific filename, accents intact', () => {
  const { html } = run({ ...BASE, posts: JSON.stringify(POSTS) });
  return html.includes('programação-e-café.md');
});

check('a finished link is appended, never rebuilt', () => {
  // The regression that made links unclickable: rewriting the container each
  // tick destroyed every anchor already typed.
  const { done } = run({ ...BASE, posts: JSON.stringify(POSTS) });
  return done.rebuilds === 0 && done.appends > 0;
});

check('a half-typed segment is never a link', () => {
  // Stop after a handful of ticks: whatever is mid-flight must not be an anchor.
  const pre = makeNode('pre');
  pre.dataset = { ...BASE, posts: JSON.stringify(POSTS) };
  const queue = [];
  global.document = { getElementById: (id) => (id === 'hero-term' ? pre : null), documentElement: { scrollHeight: 0 }, createElement: makeNode, addEventListener: () => {} };
  global.window = { matchMedia: () => ({ matches: false }), addEventListener: () => {}, scrollY: 0, innerHeight: 0 };
  global.setTimeout = (fn) => queue.push(fn);
  new Function(fs.readFileSync(SRC, 'utf8'))();
  let sawTailContent = false;
  for (let i = 0; i < 4000 && queue.length; i++) {
    queue.shift()();
    const tail = pre.children[1];
    if (tail && tail.innerHTML) {
      sawTailContent = true;
      if (tail.innerHTML.includes('<a ')) return false;
    }
  }
  return sawTailContent;
});

check('no listing when the site has no posts', () => !run({ ...BASE, posts: '[]' }).html.includes('ls ~/blog'));
check('no listing when the attribute is absent', () => !run({ ...BASE }).html.includes('ls ~/blog'));
check('malformed JSON degrades to no listing', () => {
  const { html } = run({ ...BASE, posts: 'not json{' });
  return !html.includes('ls ~/blog') && html.includes('whoami');
});
check('null payload does not crash the script', () => {
  const { html } = run({ ...BASE, posts: 'null' });
  return html.includes('whoami') && !html.includes('ls ~/blog');
});

check('the other three commands still render', () => {
  const { html } = run({ ...BASE, posts: '[]' });
  return html.includes('whoami') && html.includes('cat stack.txt') && html.includes('ls projects/');
});

/* A command with nothing under it is not typed at all — the rule the blog
   listing already followed, now covering the other two. The check above is the
   other half of it: a command that DOES have output must still render, or an
   over-eager skip would empty the terminal and every check here would agree. */
check('an empty stack drops cat stack.txt', () => {
  const { html } = run({ ...BASE, stack: '', posts: '[]' });
  return !html.includes('cat stack.txt') && html.includes('ls projects/');
});

check('empty projects drops ls projects/', () => {
  const { html } = run({ ...BASE, projects: '', posts: '[]' });
  return !html.includes('ls projects/') && html.includes('cat stack.txt');
});

check('with nothing to list, only whoami and the trailing prompt are typed', () => {
  const { html } = run({ ...BASE, stack: '', projects: '', posts: '[]' });
  // Asserted as the whole script, not as three absences: an extra blank line or
  // a stray prompt is exactly the kind of thing `includes` would not notice.
  return html.replace(/<[^>]*>/g, '') === 'a@b:~$ whoami\nN — R · L\n\na@b:~$ ';
});

check('the blog listing still renders when the other two are gone', () => {
  const { html } = run({ ...BASE, stack: '', projects: '', posts: JSON.stringify(POSTS) });
  return html.includes('ls ~/blog --latest') && html.includes('migrando-o-trailhead-para-o-nuxt-3.md') &&
    !html.includes('cat stack.txt') && !html.includes('ls projects/');
});

check('a post with no date renders without a date column', () => {
  const { html } = run({ ...BASE, posts: JSON.stringify([{ d: '', f: 'x.md', t: 'X', u: '/x/' }]) });
  return html.includes('x.md') && !html.includes('0001-01-01');
});

check('reduced motion renders the links immediately', () => {
  const { done, tail, html } = run({ ...BASE, posts: JSON.stringify(POSTS) }, { reduceMotion: true, runTimers: false });
  return (html.match(/<a href=/g) || []).length === 2 && tail.innerHTML === '' && done.rebuilds === 1;
});

check('markup in a title or filename is escaped', () => {
  const { html } = run({ ...BASE, posts: JSON.stringify([{ d: '2026-01-01', f: '<script>x</script>.md', t: 'a"b', u: '/ok/' }]) });
  return !html.includes('<script>') && html.includes('&lt;script&gt;') && html.includes('aria-label="a&quot;b"');
});

check('a quote in the URL cannot break out of the href', () => {
  const { html } = run({ ...BASE, posts: JSON.stringify([{ d: '2026-01-01', f: 'x.md', t: 'X', u: '/a"onmouseover="alert(1)' }]) });
  return html.includes('&quot;onmouseover=') && !/href="[^"]*"\s*onmouseover/.test(html);
});

/* ---- the reserved height ----
   hero.html counts the lines it emits and the CSS turns them into a min-height,
   so the box does not grow under the reader while this types. Both sides count
   LOGICAL lines and the body wraps, so on a phone the reservation fell short and
   the box grew line by line anyway. The script now measures the box and counts
   the rows the text really takes, which is why the wrapping is checked here:
   every check CI runs is width-independent by construction — it recomputes the
   count from the same data-* attributes the template read — so no build could
   ever see a wrap.

   The fixture is the exampleSite's own hero, attribute for attribute, at the
   viewport the bug was measured on: 360x800, leaving the body 290px of inner
   width, 12px JetBrains Mono, so 40 characters to a row. Five of its fifteen
   lines run past that. */
const SITE = {
  user: 'robin@portfolio',
  name: 'Robin Vale',
  role: 'Front-End Developer',
  loc: 'Berlin, Germany',
  stack: 'JavaScript · Vue.js · React · HTML5 · CSS3 · SASS',
  projects: 'trailhead/   neon-drift/   sprint-deck/',
  posts: JSON.stringify([
    { d: '2026-03-12', f: 'migrating-trailhead-to-nuxt-3.md', t: 'Migrating Trailhead to Nuxt 3', u: '/blogs/trailhead-nuxt-3/' },
    { d: '2026-02-27', f: 'generating-chiptune-audio-with-the-….md', t: 'Generating chiptune audio with the Web Audio API', u: '/blogs/chiptune-web-audio-api/' },
    { d: '2026-02-08', f: 'real-time-planning-poker-with-socke….md', t: 'Real-time Planning Poker with Socket.IO', u: '/blogs/planning-poker-socketio/' },
  ]),
};
const PHONE = { width: 290, char: 7.2 };
// The desktop column: half of a 1080px container, 14px type. Nothing wraps there,
// which is why the bug was invisible to anyone looking at it on a laptop.
const DESKTOP = { width: 498, char: 8.4 };

check('the reserved height counts the rows the text takes, not the lines it is written in', () => {
  // 15 logical lines, 20 rows: the whoami line, the stack, and all three post
  // filenames each take two. 15 lines reserved 369px for 480px of text.
  return run(SITE, PHONE).lines === '20';
});

check('where nothing wraps, the count is the template\'s own arithmetic', () => {
  // 4 + 3 + 3 + (2 + 3) — the same sum hero.html does in Go and CI redoes in
  // Python. The script may only ever add rows a wrap costs, never invent one.
  return run(SITE, DESKTOP).lines === '15';
});

check('a filename too long for the whole row is split, not counted once', () => {
  // word-break:break-word splits a word that has no break opportunity in it, so
  // a row is not the ceiling. At 26 columns the listing line — a 10-character
  // date, two spaces, a 32-character filename — takes three rows: the date, then
  // the filename broken 26 + 6. Seven logical lines, nine rows.
  const one = { d: '2026-03-12', f: 'migrating-trailhead-to-nuxt-3.md', t: 'T', u: '/u/' };
  const { lines } = run({ ...BASE, stack: '', projects: '', posts: JSON.stringify([one]) },
    { width: 260, char: 10 });
  return lines === '9';
});

check('a box that measures nothing leaves the template count alone', () => {
  // No layout engine, a hidden hero, a zero-width column: the server-rendered
  // number is the best available and must not be overwritten by a guess.
  return run(SITE).lines === undefined;
});

check('a rotate re-reserves at the new width', () => {
  // The count is worked out once before typing starts; the phone can turn while
  // it types, and a portrait reservation is wrong in landscape.
  const r = run(SITE, PHONE);
  return r.lines === '20' && r.resize(498) === '15';
});

check('a resize that leaves the width alone does not re-measure', () => {
  // Chrome fires resize on the address bar collapsing and on every frame of a
  // desktop drag; only a change of width can change the count. Resized to the
  // same width but with an advance twice as wide — which would show up in the
  // count immediately if the guard were not there.
  const r = run(SITE, PHONE);
  return r.lines === '20' && r.resize(290, 14.4) === '20';
});

let failed = 0;
for (const [name, fn] of checks) {
  let ok = false;
  let err = '';
  try { ok = fn() === true; } catch (e) { err = ' — threw: ' + e.message; }
  if (!ok) failed++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${err}`);
}
console.log(`\n${checks.length - failed}/${checks.length} passed`);
process.exit(failed ? 1 : 0);
