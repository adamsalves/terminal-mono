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
  function s(t, c) { return { t: t, c: c }; }

  var segs = [
    s(prompt, C.prompt), s(':~$ ', C.sep), s('whoami\n', C.cmd),
    s(name + ' — ' + role + (loc ? ' · ' + loc : '') + '\n\n', C.out1),
    s(prompt, C.prompt), s(':~$ ', C.sep), s('cat stack.txt\n', C.cmd),
    s(stack + '\n\n', C.out2),
    s(prompt, C.prompt), s(':~$ ', C.sep), s('ls projects/\n', C.cmd),
    s(projects + '\n\n', C.out2),
    s(prompt, C.prompt), s(':~$ ', C.sep)
  ];

  var cursor = '<span style="display:inline-block;width:9px;height:16px;background:#b6ff3c;vertical-align:-3px;margin-left:2px;animation:blink 1.1s steps(1) infinite;"></span>';

  function esc(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function build(upto, partial) {
    var html = '';
    for (var i = 0; i < upto; i++) {
      html += '<span style="color:' + segs[i].c + '">' + esc(segs[i].t) + '</span>';
    }
    if (upto < segs.length && partial > 0) {
      var seg = segs[upto];
      html += '<span style="color:' + seg.c + '">' + esc(seg.t.slice(0, partial)) + '</span>';
    }
    return html;
  }

  if (reduce) {
    pre.innerHTML = build(segs.length, 0) + cursor;
    return;
  }

  var si = 0, ci = 0;
  function tick() {
    if (si >= segs.length) { pre.innerHTML = build(segs.length, 0) + cursor; return; }
    var seg = segs[si];
    ci++;
    if (ci > seg.t.length) { si++; ci = 0; setTimeout(tick, 0); return; }
    pre.innerHTML = build(si, ci) + cursor;
    var ch = seg.t[ci - 1];
    setTimeout(tick, ch === '\n' ? 80 : 15);
  }
  setTimeout(tick, 400);
})();
