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
    /* The typewriter's tail is a text node whose .data is reassigned, so what a
     * node "contains" is no longer only its innerHTML. Reading both is what lets
     * a test still see a half-typed segment. */
    get text() {
      return this._html + this.children.map((c) => (c.nodeType === 3 ? c.data : c.text)).join('');
    },
    /* The script measures with two nested probes and marks each one with
     * data-probe, so this reads the role instead of inferring it from the shape
     * of the tree: a stub that guessed would keep answering confidently — and
     * wrongly — if the probes were ever restructured. */
    getBoundingClientRect() {
      if (this.attrs['data-probe'] === 'box') return { width: metrics.width };
      return { width: this._html.length * metrics.char };
    },
  };
}

/* A text node. The script reassigns .data on one of these instead of rebuilding
 * the tail's markup — writes counted so a test can assert the parser is never
 * involved, which is the whole point of the change. */
function makeText(data) {
  return { nodeType: 3, _data: data || '', writes: 0,
           set data(v) { this._data = v; this.writes++; },
           get data() { return this._data; } };
}

/* One frame is 16ms of the fake clock. The typewriter budgets in milliseconds
 * and writes once per frame, so the harness has to hand it a moving timestamp —
 * a stub that always said 0 would credit no time and never type anything. */
const FRAME_MS = 16;

/* The <pre>'s children minus the measurement probe. The probe used to be created
 * and destroyed inside one call and was never visible from here; it is kept in
 * place now, so position in the child list is no longer a reliable way to find
 * the two regions the typewriter writes into. It carries data-probe, so ask. */
function typed(pre) {
  return pre.children.filter((c) => !c.attrs || !c.attrs['data-probe']);
}

function run(dataset, { reduceMotion = false, runTimers = true, width = 0, char = 0,
                       resizeObserver = true, frameMs = FRAME_MS,
                       docHeight = 0, viewport = 0, scrollY = 0 } = {}) {
  const pre = makeNode('pre');
  pre.dataset = dataset;
  pre.clientWidth = width;
  metrics = { width, char };

  /* The reading-progress bar, which getElementById used to answer null for —
   * leaving the whole block dead code in here and the only script the theme
   * ships half covered. docHeight and viewport are the two numbers its
   * arithmetic runs on; both default to 0, which is the page that cannot
   * scroll. */
  const progress = makeNode('div');

  const queue = [];
  const listeners = {};
  // ResizeObserver is what the script reaches for first, so it is what the tests
  // drive; `resizeObserver: false` takes it away to exercise the window fallback.
  // The real one calls back once on observe, and this does too.
  const observers = [];
  if (resizeObserver) {
    global.ResizeObserver = function (cb) {
      this.observe = () => { observers.push(cb); cb(); };
    };
  } else {
    delete global.ResizeObserver;
  }
  // font-display:swap: JetBrains Mono can land after the first reservation. A
  // thenable rather than a real promise, so a test fires it where it can see the
  // result instead of on a later microtask.
  const fontCbs = [];
  global.document = {
    getElementById: (id) => (id === 'hero-term' ? pre : id === 'progress' ? progress : null),
    documentElement: { scrollHeight: docHeight },
    createElement: makeNode,
    createTextNode: makeText,
    addEventListener: () => {},
    fonts: { ready: { then: (fn) => { fontCbs.push(fn); } } },
  };
  const frames = [];
  global.window = {
    matchMedia: () => ({ matches: reduceMotion }),
    addEventListener: (type, fn) => { (listeners[type] = listeners[type] || []).push(fn); },
    requestAnimationFrame: (fn) => frames.push(fn),
    scrollY,
    innerHeight: viewport,
  };
  /* Captured, not read back off `global` later. The helpers below outlive the
   * call that made them — a second run() reassigns global.window, and a handle
   * from the first would then report the second's geometry. `metrics` has the
   * same shape of problem one level down and is documented where it is defined;
   * this one is cheap to simply not have. */
  const win = global.window;
  global.setTimeout = (fn) => { queue.push(fn); return queue.length; };

  new Function(fs.readFileSync(SRC, 'utf8'))();

  // Drain the typewriter. Each frame schedules the next one; cap it so a runaway
  // loop fails the test instead of hanging CI. The timer queue is drained too,
  // because the measurement path still uses it — nothing else schedules there
  // while requestAnimationFrame exists.
  //
  // The one path this harness cannot exercise is terminal.js's own fallback for
  // a browser with no requestAnimationFrame, which calls setTimeout(fn, 16) and
  // reads Date.now(). The queue here drains instantly, so that clock never
  // advances, no character ever comes due and the loop runs until the guard
  // below stops it. In a browser the clock is real and it types. Covering it
  // would take a fake clock the timer stub advances, which is a harness change
  // for a branch no browser with ResizeObserver — which this script also
  // requires — has taken since 2012.
  let guard = 0;
  let clock = 0;
  let frameCount = 0;
  while (runTimers && (queue.length || frames.length)) {
    if (++guard > 500000) throw new Error('typewriter did not terminate');
    if (frames.length) {
      clock += frameMs;
      frameCount++;
      frames.shift()(clock);
    } else {
      queue.shift()();
    }
  }

  const [done, tail] = typed(pre);
  return {
    pre,
    done,
    tail,
    frames: frameCount,
    // What the batching is actually about: how many times the tail's text node
    // was assigned. Counting frames instead was counting the loop, not the work.
    writes: (function count(node) {
      return node.children.reduce(
        (n, c) => n + (c.nodeType === 3 ? c.writes : count(c)), 0);
    })(pre),
    // The tail's text lives in a text node now, so `text` is what reads it. done
    // is still markup — completed segments go through wrap(), which is where the
    // escaping and the anchors happen.
    html: (done ? done.innerHTML : '') + (tail ? tail.text : ''),
    // The height the box reserves, in lines. undefined when the script left the
    // template's own count standing.
    lines: pre.style.props['--hero-lines'],
    // Rotate the phone: a new width — and optionally a new advance, so a test can
    // tell a reservation that was re-measured from one that was left alone.
    resize(w, ch = char) {
      pre.clientWidth = w;
      metrics = { width: w, char: ch };
      observers.forEach((fn) => fn());
      (listeners.resize || []).forEach((fn) => fn());
      return pre.style.props['--hero-lines'];
    },
    // The web font arrives: same box, a different advance.
    fontsReady(ch) {
      metrics = { width: metrics.width, char: ch };
      fontCbs.forEach((fn) => fn());
      return pre.style.props['--hero-lines'];
    },
    // Scroll to y and read the bar back. Any frames the handler queued are
    // drained afterwards, so this reads the same whether the bar writes inside
    // the event or on the next frame — what is asserted is where the bar ends
    // up, not which of the two ways it got there.
    scroll(y) {
      win.scrollY = y;
      (listeners.scroll || []).forEach((fn) => fn());
      const queued = frames.length;
      for (let i = 0; i < queued; i++) frames.shift()(0);
      return progress.style.width;
    },
    // A resize with no scroll. The bar listens for it because the document's
    // height is what the percentage divides by, and that changes when the
    // viewport does — a listener nothing exercised until now.
    resizeViewport(h) {
      win.innerHeight = h;
      (listeners.resize || []).forEach((fn) => fn());
      const queued = frames.length;
      for (let i = 0; i < queued; i++) frames.shift()(0);
      return progress.style.width;
    },
    // Where the bar was left before anything scrolled.
    get progressWidth() { return progress.style.width; },
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

/* Runs the script and stops mid-animation, handing back the state at each frame.
 * The full-drain `run` above cannot see any of this: by the time it returns the
 * tail is empty and every segment has been committed. */
function runPartial(dataset, frameLimit, frameMs = FRAME_MS) {
  const pre = makeNode('pre');
  pre.dataset = dataset;
  pre.clientWidth = 0;
  metrics = { width: 0, char: 0 };
  const queue = [];
  const frames = [];
  global.document = {
    getElementById: (id) => (id === 'hero-term' ? pre : null),
    documentElement: { scrollHeight: 0 },
    createElement: makeNode,
    createTextNode: makeText,
    addEventListener: () => {},
  };
  global.window = {
    matchMedia: () => ({ matches: false }),
    addEventListener: () => {},
    requestAnimationFrame: (fn) => frames.push(fn),
    scrollY: 0,
    innerHeight: 0,
  };
  global.setTimeout = (fn) => queue.push(fn);
  delete global.ResizeObserver;
  new Function(fs.readFileSync(SRC, 'utf8'))();
  const states = [];
  let clock = 0;
  for (let i = 0; i < frameLimit && frames.length; i++) {
    clock += frameMs;
    frames.shift()(clock);
    const [done, tail] = typed(pre);
    states.push({ tail, text: tail ? tail.text : '', done });
  }
  return { pre, states };
}

check('a half-typed segment is never a link', () => {
  // A text node cannot be an anchor, which is the point — but the tail's own
  // children must not become one either, and the text must actually be arriving
  // or this passes by never looking at anything.
  const { pre, states } = runPartial({ ...BASE, posts: JSON.stringify(POSTS) }, 4000);
  let sawTailContent = false;
  for (const st of states) {
    if (st.text) sawTailContent = true;
    if (st.tail.innerHTML.includes('<a ')) return false;
    if (st.tail.children.some((c) => c.nodeType !== 3 && c.tagName === 'A')) return false;
  }
  return sawTailContent;
});

check('the measurement probe never outlives the measurement', () => {
  // Keeping one was tried and rejected: it does not move forced-reflow-insight,
  // and it leaves the ruler's "0123456789" inside the terminal's textContent for
  // the life of the page — invisible to a reader and read by anything that
  // extracts text from the rendered DOM.
  const r = run({ ...BASE, posts: JSON.stringify(POSTS) }, { width: 400, char: 8 });
  const probes = () => r.pre.children.filter((c) => c.attrs && c.attrs['data-probe']);
  r.resize(360);
  r.fontsReady(9);
  return probes().length === 0;
});

check('the tail is never rebuilt through the HTML parser', () => {
  // The 442 innerHTML assignments this replaced each destroyed and rebuilt a
  // node identical to the one before it. Nothing may assign to the tail at all.
  const { tail } = run({ ...BASE, posts: JSON.stringify(POSTS) });
  return tail.rebuilds === 0 && tail.appends === 0;
});

check('the tail reuses one span and one text node for the whole animation', () => {
  const { states } = runPartial({ ...BASE, posts: JSON.stringify(POSTS) }, 4000);
  const span = states[0].tail.children[0];
  const text = span.children[0];
  return text.nodeType === 3 && text.writes > 0 &&
    states.every((st) => st.tail.children.length === 1 &&
                         st.tail.children[0] === span &&
                         span.children.length === 1 &&
                         span.children[0] === text);
});

check('one write per frame, not one per character', () => {
  // 40ms frames on a throttled profile: two to three characters come due in each
  // one, and they cost a single write between them.
  //
  // Compared on writes rather than frames. Writes were frames by construction,
  // so asserting on frames was asserting that the loop ran — true of any
  // implementation, including the one this replaced. The number that has to
  // move is the number of times the DOM was touched.
  //
  // Two thirds rather than a half: skipping the frames where nothing changed
  // took 54 writes off the fast profile, which is the improvement working and
  // also what narrows the gap between the two. Measured 104 against 204.
  const slow = run({ ...BASE, posts: JSON.stringify(POSTS) }, { frameMs: 40 });
  const fast = run({ ...BASE, posts: JSON.stringify(POSTS) }, { frameMs: 16 });
  return slow.frames > 0 && slow.writes > 0 && slow.writes * 3 < fast.writes * 2;
});

check('a frame where no character came due writes nothing', () => {
  // The opening pause is ~25 frames long and nothing changes in any of them.
  // Assigning the same string still marks the node dirty, so the guard is the
  // difference between "one write per frame" and "one write per frame that
  // changed something".
  const fast = run({ ...BASE, posts: JSON.stringify(POSTS) }, { frameMs: 16 });
  return fast.writes < fast.frames;
});

check('a frame the reader was away for resumes typing instead of skipping it', () => {
  // A backgrounded tab hands back one enormous delta. Spending it would paint
  // the rest of the terminal at once, which is the animation being skipped.
  // Ten frames of a minute each. Uncapped that is ten minutes of budget and the
  // whole terminal in one paint; capped at 100ms it is a second of typing.
  const { states } = runPartial({ ...BASE, posts: JSON.stringify(POSTS) }, 10, 60000);
  const last = states[states.length - 1];
  const printed = last.done.innerHTML + last.text;
  return printed.length > 0 && !printed.includes('ls ~/blog');
});

check('the opening pause is still there', () => {
  // 400ms before the first character. At 16ms a frame that is 25 frames of
  // nothing, and a change that dropped it would show up here rather than as a
  // reader noticing the terminal no longer waits.
  const { states } = runPartial({ ...BASE, posts: '[]' }, 24);
  return states.every((st) => st.text === '' && st.done.innerHTML === '');
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

check('a full-width glyph costs two cells, not one', () => {
  // The ruler measures a digit, and a CJK glyph is twice that by design — so a
  // count of code units models a Japanese hero at half its real width and comes
  // out short, which is this bug reintroduced by its own fix. 8 + 12 glyphs
  // around an em dash is 43 cells against 40 columns, so the identity line takes
  // two rows and the terminal is five. Counted in code units it is 23 cells, the
  // line fits, and the script hands back the template's own 4 — nothing reserved.
  const jp = { user: 'a@b', name: '東京都渋谷区在住', role: 'フロントエンド開発者です',
    loc: '', stack: '', projects: '', posts: '[]' };
  return run(jp, PHONE).lines === '5';
});

check('the cursor is given a place on the line it comes to rest on', () => {
  // The cursor is an inline-block 9px wide with a 2px margin and belongs to no
  // segment, so nothing in the text accounts for it. Here the closing prompt
  // fills the row exactly: with the cursor it wraps, without it the last line
  // costs one row and the terminal is 5 rather than 6.
  const long = { user: 'a'.repeat(16), name: 'N', role: 'R', loc: '', stack: '',
    projects: '', posts: '[]' };
  return run(long, { width: 200, char: 10 }).lines === '6';
});

check('a box that measured nothing is not recorded as measured', () => {
  // The hero can be laid out later than this runs — a closed <details>, a tab
  // that is not showing. Marking the width done before anything was measured is
  // what makes the re-measure at that same width the one that gets skipped, and
  // the reader keeps the template's count forever.
  const r = run(SITE, { width: 290, char: 0 });
  return r.lines === undefined && r.resize(290, 7.2) === '20';
});

check('the web font arriving re-measures at the same width', () => {
  // font-display:swap: the first reservation is against the fallback's advance,
  // and JetBrains Mono is not the same width. The width guard would refuse this
  // one, so it is forced. Twice the advance halves the columns: 20 rows, then 31.
  const r = run(SITE, PHONE);
  return r.lines === '20' && r.fontsReady(14.4) === '31';
});

check('reduced motion reserves the height it prints in one go', () => {
  // The whole script is written out at once, so nothing grows — but the box is
  // still a min-height in a centred grid, and the reservation runs before the
  // early return that renders it.
  return run(SITE, { ...PHONE, reduceMotion: true }).lines === '20';
});

check('without ResizeObserver, the window resize is still the fallback', () => {
  // ResizeObserver watches the box, which is the only one of the two that sees a
  // hero given a layout after this ran. Where it is missing, a rotate has to keep
  // working through the listener this shipped with.
  const r = run(SITE, { ...PHONE, resizeObserver: false });
  return r.lines === '20' && r.resize(498, 8.4) === '15';
});

/* The reading-progress bar. A page 4000px tall in an 800px viewport: 3200px of
 * travel, so scrollY 800 is a quarter of the way down. Round numbers because the
 * assertions are on the string the bar is handed, and the percentage is not
 * rounded anywhere — 1601 would read back as "50.03125%".
 *
 * These describe what the bar shows, not how it is scheduled: a version that
 * writes inside the scroll event and a version that writes on the next frame
 * both have to satisfy them. That is deliberate. The scheduling was measured in
 * a browser (Chrome coalesces scroll into the frame lifecycle, so the handler
 * already ran about once a frame — 0.14 events per frame under 6x CPU) and there
 * was nothing there to win; what there was, was a script the theme ships with a
 * whole block no test ever entered. */
const PAGE = { ...PHONE, docHeight: 4000, viewport: 800 };

check('the progress bar is painted before anything scrolls', () => {
  // Landing mid-document — a deep link, a scroll position the browser restored —
  // has to show the bar where the reader already is, not at zero until they move.
  // scrollY is what makes this the stated scenario rather than a check that the
  // initial paint merely happened: at 0 it reads '0%' either way.
  return run(SITE, { ...PAGE, scrollY: 1600 }).progressWidth === '50%';
});

check('the bar reports how far down the document the reader is', () => {
  return run(SITE, PAGE).scroll(800) === '25%';
});

check('a document with nowhere to scroll leaves the bar at zero', () => {
  // A viewport as tall as the page, or taller, makes the denominator zero or
  // negative — the inputs that turn the percentage into NaN% and -50%.
  //
  // Both are scrolled on purpose. The obvious fixture, `scrollY: 0` against a
  // negative denominator, cannot fail: `0 / -400 * 100` is -0, and `String(-0)`
  // is "0", so it reads '0%' with the guard removed and passes a version that
  // has no guard at all. Verified by deleting `h > 0 ? … : 0` — the suite stayed
  // green. These two do not: unguarded they read '-50%' and 'NaN%'.
  const negative = run(SITE, { ...PAGE, docHeight: 400 });   // h = -400
  const exact = run(SITE, { ...PAGE, docHeight: 800 });      // h = 0
  return negative.progressWidth === '0%' && negative.scroll(200) === '0%'
      && exact.scroll(100) === '0%';
});

check('a resize with no scroll re-reads the height the bar divides by', () => {
  // The bar listens for resize because the denominator is the document height
  // minus the viewport, and the second term is what a rotate changes. Halving
  // the viewport of a reader standing still moves them from a quarter down to
  // a fifth, without a scroll event anywhere.
  const r = run(SITE, { ...PAGE, scrollY: 800 });
  return r.progressWidth === '25%' && r.resizeViewport(400) === '22.22222222222222%';
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
