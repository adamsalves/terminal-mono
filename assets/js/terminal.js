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

  var C = { prompt: '#6f8f3a', sep: '#8c9384', cmd: '#e9e7df', out1: '#b6ff3c', out2: '#9aa193' };
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
     gone before this returns, so neither is ever painted. */
  var RULER = '0123456789';
  function columns() {
    var box = document.createElement('span');
    box.setAttribute('style', 'display:block;height:0;overflow:hidden;visibility:hidden');
    var ruler = document.createElement('span');
    ruler.setAttribute('style', 'white-space:pre');
    ruler.textContent = RULER;
    box.appendChild(ruler);
    pre.appendChild(box);
    var width = box.getBoundingClientRect().width;
    var advance = ruler.getBoundingClientRect().width / RULER.length;
    pre.removeChild(box);
    /* A hidden hero, a zero-width column, a DOM that does not lay anything out:
       nothing to measure, so the template's count stands rather than being
       replaced by a guess. */
    if (!(width > 0) || !(advance > 0)) return 0;
    return Math.max(1, Math.floor(width / advance + 0.01));
  }

  /* How many rows one logical line takes in `cols` characters, by the rule the
     browser applies: fill the row with whole words, push a word that does not fit
     onto the next one, and split it mid-word only when it would not fit on a row
     of its own. Trailing spaces hang past the edge instead of forcing a wrap, so
     a run of them can fill a row but never start one.
     Measured in characters, which the monospace body makes equivalent to width.
     Two approximations, both deliberately in the same direction: a grapheme
     spelled with more than one code unit — an emoji, an accented name in NFD —
     counts as several, and a hyphen inside a word is a break opportunity the
     browser will take and this will not, so a word moves down whole where the
     browser would have filled the row first. Neither can pack a line tighter than
     the browser does, so the count is never short — and of the two mistakes, dead
     space is the one the reader does not see. */
  function rows(line, cols) {
    var n = 1, used = 0;
    var parts = line.match(/\s+|\S+/g) || [];
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i], len = part.length;
      if (/\s/.test(part.charAt(0))) { used = Math.min(used + len, cols); continue; }
      if (used + len <= cols) { used += len; continue; }
      if (used) { n++; used = 0; }
      if (len <= cols) { used = len; continue; }
      n += Math.ceil(len / cols) - 1;
      used = len % cols || cols;
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
    measuredAt = w;
    var cols = columns();
    if (!cols) return;
    var text = '';
    for (var i = 0; i < segs.length; i++) text += segs[i].t;
    /* No segment ends the script with a newline, so this is the same set of
       logical lines the template counted — each one now costing what it really
       costs. */
    var lines = 0, logical = text.split('\n');
    for (var j = 0; j < logical.length; j++) lines += rows(logical[j], cols);
    pre.style.setProperty('--hero-lines', String(lines));
  }

  reserve(true);
  /* The width belongs to the viewport and the advance to the loaded font, and
     both can move after this first pass: a rotate changes one, JetBrains Mono
     arriving under font-display:swap changes the other, either of them while the
     text is still being typed. */
  window.addEventListener('resize', function () { reserve(false); });
  if (document.fonts && document.fonts.ready && document.fonts.ready.then) {
    document.fonts.ready.then(function () { reserve(true); });
  }

  var cursorStyle = 'display:inline-block;width:9px;height:16px;background:#b6ff3c;vertical-align:-3px;margin-left:2px;animation:blink 1.1s steps(1) infinite;';

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

  var si = 0, ci = 0;
  function tick() {
    if (si >= segs.length) return;
    var seg = segs[si];
    ci++;
    if (ci > seg.t.length) {
      /* Segment finished: hand it to the stable region and clear the cursor's
         scratch space. insertAdjacentHTML appends without touching what is
         already there, so earlier links survive untouched. */
      doneEl.insertAdjacentHTML('beforeend', wrap(seg, seg.t, true));
      tailEl.textContent = '';
      si++; ci = 0;
      setTimeout(tick, 0);
      return;
    }
    tailEl.innerHTML = wrap(seg, seg.t.slice(0, ci), false);
    var ch = seg.t[ci - 1];
    setTimeout(tick, ch === '\n' ? 80 : 15);
  }
  setTimeout(tick, 400);
})();
