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

  var segs = [
    s(prompt, C.prompt), s(':~$ ', C.sep), s('whoami\n', C.cmd),
    s(name + ' — ' + role + (loc ? ' · ' + loc : '') + '\n\n', C.out1)
  ];

  /* A command whose output is empty is not typed at all — the rule the blog
     listing below has always followed, applied to the other two. Without it a
     site that has no skills or no projects, or that turned those sections off,
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
