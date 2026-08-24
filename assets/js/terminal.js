/* ============================================================
   Terminal Mono — vanilla JS, no dependencies:
   hamburger menu, reading-progress bar and the hero typewriter
   effect. Respects prefers-reduced-motion.
   ============================================================ */
(function () {
  'use strict';

  /* ---- hamburger menu (mobile) ---- */
  var burger = document.getElementById('hamburger');
  var menu = document.getElementById('mobile-menu');
  if (burger && menu) {
    burger.addEventListener('click', function () {
      var open = menu.classList.toggle('open');
      burger.classList.toggle('open', open);
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    menu.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        menu.classList.remove('open');
        burger.classList.remove('open');
        burger.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ---- reading-progress bar ---- */
  var bar = document.getElementById('progress');
  if (bar) {
    var update = function () {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.width = (h > 0 ? (window.scrollY / h) * 100 : 0) + '%';
    };
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    update();
  }

  /* ---- hero terminal typewriter effect ---- */
  var pre = document.getElementById('hero-term');
  if (!pre) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var d = pre.dataset;
  var name = d.name || '';
  var role = d.role || '';
  var loc = d.loc || '';
  var stack = d.stack || '';
  var projects = d.projects || '';

  /* The five colors the script paints with, named rather than spelled. These
     go straight into a style= attribute, so `var(--accent-dim)` is a value the
     browser resolves against whatever palette is on <html> — including a
     [params.theme.colors] override, which arrives as CSS this file never sees.
     Reading them back with getComputedStyle would work too, and would have to
     pick a moment after the stylesheet applied; there is no such moment to get
     wrong when the value is never resolved here at all. */
  var C = {
    prompt: 'var(--accent-dim)',
    sep: 'var(--muted-2)',
    cmd: 'var(--text)',
    out1: 'var(--accent)',
    out2: 'var(--muted)'
  };
  var prompt = (d.user || 'adams@portfolio');
  /* u is optional: a segment carrying one renders as a link instead of a span.
     a is the link's accessible name, since the visible text is a filename. */
  function s(t, c, u, a) { return { t: t, c: c, u: u, a: a }; }

  /* whoami is the one command that always runs, and the rule below does not
     apply to it: its output is the page's own identity, not a section's data, so
     no switch can empty it and there is nothing to test. A site that fills
     nothing in still gets the em dash on its own line. */
  var segs = [
    s(prompt, C.prompt), s(':~$ ', C.sep), s('whoami\n', C.cmd),
    s(name + ' — ' + role + (loc ? ' · ' + loc : '') + '\n\n', C.out1)
  ];

  /* Every other command whose output is empty is not typed at all — the rule the
     blog listing below has always followed, applied to the other two. Without it
     a site that has no skills or no projects, or that turned those sections off,
     still got the command and a blank line under it. */
  if (stack) {
    segs.push(s(prompt, C.prompt), s(':~$ ', C.sep), s('cat stack.txt\n', C.cmd),
      s(stack + '\n\n', C.out2));
  }
  if (projects) {
    segs.push(s(prompt, C.prompt), s(':~$ ', C.sep), s('ls projects/\n', C.cmd),
      s(projects + '\n\n', C.out2));
  }

  /* The blog listing, when the site has posts. data-posts is JSON rather than a
     delimited string like data-stack: each entry is a filename paired with its
     URL, and any delimiter could turn up inside a slug. */
  /* Anything other than an array is treated as no listing. JSON.parse("null")
     returns null rather than throwing, and a TypeError here would take the whole
     IIFE down with it — including the hamburger menu and the progress bar. */
  var posts = [];
  try { posts = JSON.parse(d.posts || '[]'); } catch (e) { posts = []; }
  if (!Array.isArray(posts)) posts = [];

  if (posts.length) {
    segs.push(s(prompt, C.prompt), s(':~$ ', C.sep), s('ls ~/blog --latest\n', C.cmd));
    posts.forEach(function (p) {
      /* The newline stays outside the link: under white-space:pre-wrap an <a>
         holding it would stretch its click target across the line break. */
      if (p.d) segs.push(s(p.d + '  ', C.out2));
      segs.push(s(p.f, C.out1, p.u, p.t), s('\n', C.out2));
    });
    segs.push(s('\n', C.out2));
  }

  segs.push(s(prompt, C.prompt), s(':~$ ', C.sep));

  /* ---- the height the terminal reserves, in visual lines ----
     hero.html counts the lines it is about to emit and hands them over as
     --hero-lines, which the CSS turns into a min-height so the box does not grow
     under the reader while this types. That count is exact only while one logical
     line renders as one visual line, and .term__body wraps (white-space:pre-wrap
     with word-break:break-word): on a 360px phone five of the exampleSite's
     fifteen lines take two rows each, so the box reserved 369px for 480px of text
     and grew line by line — the exact shift the reservation exists to prevent, on
     the viewport where it is scored hardest.
     Only the browser knows the body's width and the font's advance, so the count
     is refined here and written back to the same variable before the first
     character is typed. The template's number stays the pre-JS and no-JS value:
     where this does not run, nothing has changed. */

  /* One probe measured twice: the block takes the body's content width, after
     whatever padding the breakpoint or a site override applies, and the digits
     inside it give one character's advance in the font actually in use. Both are
     gone before this returns — the removal sits in a finally, because a probe left
     behind by a throw would stay in the <pre> for the life of the page — so
     neither is ever painted. */
  var RULER = '0123456789';
  /* The cursor is an inline-block 9px wide carrying a 2px margin, and it belongs to
     no segment's text, so the line it lands on has to be told about it: it cannot
     be split, and with only a space in front of it, it can be pushed to a row of
     its own. */
  var CURSOR_PX = 11;
  function metrics() {
    var box = document.createElement('span');
    box.setAttribute('style', 'display:block;height:0;overflow:hidden;visibility:hidden');
    var ruler = document.createElement('span');
    ruler.setAttribute('style', 'white-space:pre');
    ruler.textContent = RULER;
    /* Says which probe is which to anything reading this from outside a browser:
       the test harness stands in for the layout engine, and with nothing to read it
       has to infer the two roles from the shape of the tree — so a change to the
       probes would leave it answering confidently with the wrong number. */
    box.setAttribute('data-probe', 'box');
    ruler.setAttribute('data-probe', 'ruler');
    box.appendChild(ruler);
    pre.appendChild(box);
    var w = 0, advance = 0;
    try {
      w = box.getBoundingClientRect().width;
      advance = ruler.getBoundingClientRect().width / RULER.length;
    } catch (e) {
      w = 0;
    } finally {
      /* The probe is built and destroyed inside this call rather than kept.
         Keeping one was tried, for the forced reflow the create/remove pair
         causes on every re-measure — and it moved nothing: `forced-reflow-insight`
         fires on about half of Lighthouse's runs either way, because what is
         being forced is the document's *first* layout, which the read below
         genuinely needs and which no amount of probe reuse removes. What a kept
         probe does do is leave "0123456789" inside the terminal's textContent
         for the life of the page — invisible to a reader, and read by anything
         that extracts text from the rendered DOM, which on this theme now
         includes the answer engines llms.txt is for. Not a trade worth making
         for a coin-flip audit. */
      pre.removeChild(box);
    }
    if (!(w > 0) || !(advance > 0)) return null;
    /* The epsilon absorbs the float error in a ratio that ought to be whole —
       39.999999996 where the box fits exactly 40 columns. It has to stay far below
       the gap to the next column: at 0.01, a box that genuinely fits 39.995 rounds
       up to 40 and the count comes out one column too generous, which is the one
       direction this must never err in. */
    return { cols: Math.max(1, Math.floor(w / advance + 1e-6)),
             cursor: Math.ceil(CURSOR_PX / advance) };
  }

  /* What one character costs, in cells. East Asian Wide and Fullwidth, and
     everything past the BMP, are two — the rule a real terminal applies and the one
     a monospace font follows by design, since the ruler above measures a digit.
     Counting them as one is the only way this can come out short: a Japanese
     subtitle would model at half its width and the box would grow under the reader
     again, which is the whole bug. Where the glyph is missing from JetBrains Mono
     and a proportional fallback serves it, two is an over-estimate — dead space,
     the mistake the reader cannot see. */
  function cells(ch) {
    var c = ch.charCodeAt(0);
    if (c < 0x1100) return 1;
    /* The low half of a surrogate pair: its high half already paid for both. */
    if (c >= 0xdc00 && c <= 0xdfff) return 0;
    return (c <= 0x115f ||
      c === 0x2329 || c === 0x232a ||
      (c >= 0x2e80 && c <= 0xa4cf && c !== 0x303f) ||
      (c >= 0xac00 && c <= 0xd7a3) ||
      (c >= 0xd800 && c <= 0xdbff) ||
      (c >= 0xf900 && c <= 0xfaff) ||
      (c >= 0xfe30 && c <= 0xfe6f) ||
      (c >= 0xff00 && c <= 0xff60) ||
      (c >= 0xffe0 && c <= 0xffe6)) ? 2 : 1;
  }
  function cellWidth(s) {
    var w = 0;
    for (var i = 0; i < s.length; i++) w += cells(s.charAt(i));
    return w;
  }

  /* How many rows one logical line takes in `cols` cells, by the rule the browser
     applies: fill the row with whole words, push a word that does not fit onto the
     next one, and split it mid-word only when it would not fit on a row of its own.
     Trailing spaces hang past the edge instead of forcing a wrap, so a run of them
     can fill a row but never start one.
     One approximation is left, and it is deliberately in the safe direction: a
     hyphen inside a word is a break opportunity the browser will take and this will
     not, so a word moves down whole where the browser would have filled the row
     first. A combining mark is the same shape of error — an accented name in NFD
     costs a cell per mark. Neither can pack a line tighter than the browser does,
     so the count is never short, and of the two mistakes dead space is the one the
     reader does not see. */
  function rows(line, cols) {
    var n = 1, used = 0;
    var parts = line.match(/\s+|\S+/g) || [];
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i], len = cellWidth(part);
      if (/\s/.test(part.charAt(0))) { used = Math.min(used + len, cols); continue; }
      if (used + len <= cols) { used += len; continue; }
      if (used) { n++; used = 0; }
      if (len <= cols) { used = len; continue; }
      /* Too long for a row of its own, so word-break splits it. Walked a cell at a
         time rather than divided: a two-cell glyph that does not fit in the last
         cell of a row moves down whole and leaves that cell empty, and a division
         cannot see the row that costs. */
      for (var k = 0; k < part.length; k++) {
        var c = cells(part.charAt(k));
        if (used + c > cols) { n++; used = 0; }
        used += c;
      }
    }
    return n;
  }

  var measuredAt = -1;
  function reserve(force) {
    /* Only a change of width can change the count, so a resize that leaves it
       alone — a vertical drag, the address bar collapsing — costs one read and
       stops there. */
    var w = pre.clientWidth;
    if (!force && w === measuredAt) return;
    var m = metrics();
    /* Recorded only once something has actually been measured. A hero with no
       layout when this first runs — a closed <details>, a tab that is not showing —
       must not have its width marked done, or the re-measure that arrives when it
       is finally shown at that same width is the one that gets skipped. */
    if (!m) return;
    measuredAt = w;
    var text = '';
    for (var i = 0; i < segs.length; i++) text += segs[i].t;
    var filler = '';
    while (filler.length < m.cursor) filler += '0';
    /* No segment ends the script with a newline, so this is the same set of
       logical lines the template counted — each one now costing what it really
       costs, and the last one carrying the cursor that comes to rest on it. */
    var lines = 0, logical = text.split('\n');
    for (var j = 0; j < logical.length; j++) {
      lines += rows(logical[j] + (j === logical.length - 1 ? filler : ''), m.cols);
    }
    pre.style.setProperty('--hero-lines', String(lines));
  }

  reserve(true);
  /* The width belongs to the viewport and the advance to the loaded font, and both
     can move after this first pass: a rotate changes one, JetBrains Mono arriving
     under font-display:swap changes the other, either of them while the text is
     still being typed.
     ResizeObserver watches the box rather than the window, which is both cheaper —
     it does not fire on the vertical drag whose result the guard would only throw
     away — and wider: it is the only one of the two that reports a hero which had
     no layout when this first ran and was given one later. The window listener
     stays as the fallback where it is missing. */
  if (typeof ResizeObserver === 'function') {
    new ResizeObserver(function () { reserve(false); }).observe(pre);
  } else {
    window.addEventListener('resize', function () { reserve(false); });
  }
  if (document.fonts && document.fonts.ready && document.fonts.ready.then) {
    document.fonts.ready.then(function () { reserve(true); });
  }

  var cursorStyle = 'display:inline-block;width:9px;height:16px;background:var(--accent);vertical-align:-3px;margin-left:2px;animation:blink 1.1s steps(1) infinite;';

  /* Escapes " as well as the text-node set, since esc() now also feeds an href. */
  function esc(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  /* Only a finished segment becomes a link. Anchoring a half-typed one would put
     a live href behind a one-character click target whose accessible name is
     whatever letter had been typed so far. */
  function wrap(seg, text, complete) {
    if (!seg.u || !complete) return '<span style="color:' + seg.c + '">' + esc(text) + '</span>';
    return '<a href="' + esc(seg.u) + '"' +
      (seg.a ? ' aria-label="' + esc(seg.a) + '"' : '') +
      ' style="color:' + seg.c + '">' + esc(text) + '</a>';
  }

  /* Three regions instead of one rewritten string. `done` only ever gets appended
     to, so a link stays the same DOM node once typed — rebuilding the whole <pre>
     every tick destroyed and recreated every anchor, which dropped clicks (mousedown
     and mouseup landed on different nodes) and lost keyboard focus within 50ms.
     It also made the render O(n²) over the animation. */
  var doneEl = document.createElement('span');
  var tailEl = document.createElement('span');
  var cursorEl = document.createElement('span');
  cursorEl.setAttribute('style', cursorStyle);
  cursorEl.setAttribute('aria-hidden', 'true');
  pre.appendChild(doneEl);
  pre.appendChild(tailEl);
  pre.appendChild(cursorEl);

  function renderAll() {
    var html = '';
    for (var i = 0; i < segs.length; i++) html += wrap(segs[i], segs[i].t, true);
    return html;
  }

  if (reduce) {
    doneEl.innerHTML = renderAll();
    return;
  }

  /* The tail is one <span> holding one text node, both built once and kept for
     the whole animation. What was here before assigned tailEl.innerHTML on every
     character, and wrap() for an unfinished segment always produces the same
     shape — a single span with a color — so every one of those 442 assignments
     ran the HTML parser to rebuild a node identical to the one it had just
     destroyed. Setting .data on a text node skips the parser entirely: the
     browser marks the node dirty and nothing is constructed.

     The span's color is the only thing that changes between segments, so it is
     set once per segment rather than once per character. */
  var tailSpan = document.createElement('span');
  var tailText = document.createTextNode('');
  tailSpan.appendChild(tailText);
  tailEl.appendChild(tailSpan);

  var START_MS = 400, CHAR_MS = 15, NEWLINE_MS = 80;
  /* A frame boundary the reader was not there for — a background tab, a laptop
     that slept, a long task — arrives as one enormous delta. Spending it would
     dump the rest of the terminal in a single paint, which is not the animation
     resuming, it is the animation being skipped. Capped, it resumes typing. */
  var MAX_FRAME_MS = 100;

  var raf = (typeof window.requestAnimationFrame === 'function')
    ? function (fn) { window.requestAnimationFrame(fn); }
    : function (fn) { setTimeout(function () { fn(Date.now()); }, 16); };

  var si = 0, ci = 0, colored = false;
  /* Milliseconds still owed before the next character appears. The animation
     opens with the same 400ms pause it always had. */
  var due = START_MS;
  var last = 0;

  /* Exactly one character, or one segment boundary. Writing the tail is the
     caller's job — inside a frame this may run several times, and the text node
     only needs the last of those values. */
  function advance() {
    var seg = segs[si];
    if (!colored) { tailSpan.setAttribute('style', 'color:' + seg.c); colored = true; }
    ci++;
    if (ci > seg.t.length) {
      /* Segment finished: hand it to the stable region and clear the cursor's
         scratch space. insertAdjacentHTML appends without touching what is
         already there, so earlier links survive untouched. */
      doneEl.insertAdjacentHTML('beforeend', wrap(seg, seg.t, true));
      tailText.data = '';
      si++; ci = 0; colored = false;
      due = 0;
      return;
    }
    due = seg.t.charAt(ci - 1) === '\n' ? NEWLINE_MS : CHAR_MS;
  }

  /* One write per frame instead of one per character.
     setTimeout(…, 15) does not align to anything: each callback wrote the DOM
     and the browser did style and layout work per write, at whatever cadence the
     timer happened to fire. On the throttled profile this was measured on — the
     one the score comes from — a frame takes long enough that two to four
     characters come due within it, and they now cost one write between them
     rather than four. On a machine fast enough to render every 16ms it is the
     same number of writes as before, minus the timer churn.
     It also stops entirely in a background tab, where rAF does not fire and the
     old timer kept typing to nobody. */
  function frame(now) {
    if (last === 0) last = now;
    var budget = now - last;
    last = now;
    if (budget > MAX_FRAME_MS) budget = MAX_FRAME_MS;
    while (si < segs.length && budget >= due) {
      budget -= due;
      advance();
    }
    /* Whatever is left of this frame is credited against the next character, so
       the animation keeps the timing it was written with rather than rounding
       every character up to a frame. */
    due -= budget;
    if (si >= segs.length) { tailText.data = ''; return; }
    tailText.data = segs[si].t.slice(0, ci);
    raf(frame);
  }
  raf(frame);
})();
