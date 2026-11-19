/* Flutter Scrolling — site behaviour: search, mobile sidebar, copy buttons,
   table-of-contents highlight, and reveal-on-scroll. No dependencies. */
(function () {
  'use strict';

  var root = document.body.getAttribute('data-root') || '';

  /* ── Mobile sidebar ─────────────────────────────────────────── */
  var sidebar = document.getElementById('sidebar');
  var toggle = document.getElementById('sidebar-toggle');
  var barrier = document.getElementById('sidebar-barrier');
  function setSidebar(open) {
    if (sidebar) sidebar.classList.toggle('open', open);
  }
  if (sidebar && toggle) {
    toggle.addEventListener('click', function () {
      setSidebar(!sidebar.classList.contains('open'));
    });
    if (barrier) barrier.addEventListener('click', function () { setSidebar(false); });
    var active = sidebar.querySelector('a.active');
    if (active && active.scrollIntoView) active.scrollIntoView({ block: 'nearest' });
  }

  /* ── Copy buttons ───────────────────────────────────────────── */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var area = document.createElement('textarea');
      area.value = text;
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      try { document.execCommand('copy'); resolve(); } catch (e) { reject(e); }
      document.body.removeChild(area);
    });
  }
  document.addEventListener('click', function (event) {
    var button = event.target.closest && event.target.closest('.copy');
    if (!button) return;
    var code = button.parentNode.querySelector('pre');
    copyText(code.innerText).then(function () {
      button.classList.add('done');
      setTimeout(function () { button.classList.remove('done'); }, 1200);
    }, function () {});
  });

  /* ── Reveal on scroll (home) ────────────────────────────────── */
  var reveals = document.querySelectorAll('.reveal');
  if (reveals.length) {
    if ('IntersectionObserver' in window) {
      var revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) entry.target.classList.add('revealed');
        });
      }, { threshold: 0.1 });
      reveals.forEach(function (el) { revealObserver.observe(el); });
    } else {
      reveals.forEach(function (el) { el.classList.add('revealed'); });
    }
  }

  /* ── "On this page" highlight ───────────────────────────────── */
  var tocLinks = document.querySelectorAll('.toc a');
  if (tocLinks.length && 'IntersectionObserver' in window) {
    var byId = {};
    tocLinks.forEach(function (link) { byId[link.getAttribute('href').slice(1)] = link; });
    var headings = Array.prototype.filter.call(
      document.querySelectorAll('.content h2[id], .content h3[id]'),
      function (h) { return byId[h.id]; }
    );
    var setCurrent = function () {
      var current = headings[0];
      for (var i = 0; i < headings.length; i++) {
        if (headings[i].getBoundingClientRect().top <= 110) current = headings[i];
      }
      tocLinks.forEach(function (link) { link.classList.remove('current'); });
      if (current && window.scrollY > 40) byId[current.id].classList.add('current');
    };
    var ticking = false;
    window.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () { ticking = false; setCurrent(); });
    }, { passive: true });
    setCurrent();
  }

  /* ── Search ─────────────────────────────────────────────────── */
  var overlay, input, list, status, results = [], selected = 0;

  function escapeHtml(text) {
    return text.replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function buildOverlay() {
    overlay = document.createElement('div');
    overlay.className = 'search-overlay';
    overlay.innerHTML =
      '<div class="search-modal" role="dialog" aria-modal="true" aria-label="Search docs">' +
      '<div class="search-head"><span>Search docs</span>' +
      '<button type="button" aria-label="Close search">×</button></div>' +
      '<input class="search-input" type="search" placeholder="Search guides, API, examples…" ' +
      'autocomplete="off" spellcheck="false" aria-label="Search">' +
      '<div class="search-status"></div><ul class="search-results"></ul></div>';
    document.body.appendChild(overlay);
    input = overlay.querySelector('input');
    list = overlay.querySelector('.search-results');
    status = overlay.querySelector('.search-status');
    overlay.addEventListener('mousedown', function (event) {
      if (event.target === overlay) closeSearch();
    });
    overlay.querySelector('button').addEventListener('click', closeSearch);
    input.addEventListener('input', runSearch);
    input.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowDown') { event.preventDefault(); select(selected + 1); }
      else if (event.key === 'ArrowUp') { event.preventDefault(); select(selected - 1); }
      else if (event.key === 'Enter') {
        var link = list.querySelectorAll('a')[selected];
        if (link) window.location.href = link.href;
      }
    });
  }

  function openSearch() {
    if (!overlay) buildOverlay();
    overlay.classList.add('open');
    document.body.classList.add('search-open');
    input.value = '';
    runSearch();
    input.focus();
  }

  function closeSearch() {
    if (!overlay) return;
    overlay.classList.remove('open');
    document.body.classList.remove('search-open');
  }

  function select(index) {
    var links = list.querySelectorAll('a');
    if (!links.length) return;
    selected = (index + links.length) % links.length;
    links.forEach(function (link, i) { link.classList.toggle('sel', i === selected); });
    links[selected].scrollIntoView({ block: 'nearest' });
  }

  function excerpt(text, tokens) {
    var lower = text.toLowerCase();
    var at = -1;
    for (var i = 0; i < tokens.length; i++) {
      var found = lower.indexOf(tokens[i]);
      if (found !== -1 && (at === -1 || found < at)) at = found;
    }
    var start = Math.max(0, at - 50);
    var slice = (start > 0 ? '…' : '') + text.slice(start, start + 170) + (text.length > start + 170 ? '…' : '');
    var html = escapeHtml(slice);
    tokens.forEach(function (token) {
      var pattern = new RegExp('(' + token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig');
      html = html.replace(pattern, '<mark>$1</mark>');
    });
    return html;
  }

  function runSearch() {
    var index = window.SEARCH_INDEX || [];
    var query = input.value.trim().toLowerCase();
    var tokens = query.split(/\s+/).filter(Boolean);
    list.innerHTML = '';
    selected = 0;
    if (!tokens.length) {
      status.textContent = 'Type to search ' + index.length + ' sections';
      return;
    }
    var scored = [];
    for (var i = 0; i < index.length; i++) {
      var entry = index[i];
      var title = entry.p.toLowerCase(), heading = entry.h.toLowerCase(), body = entry.x.toLowerCase();
      var score = 0, ok = true;
      for (var t = 0; t < tokens.length; t++) {
        var token = tokens[t], hit = 0;
        if (heading.indexOf(token) !== -1) hit += heading.indexOf(token) === 0 ? 20 : 12;
        if (title.indexOf(token) !== -1) hit += entry.a === '' ? (title.indexOf(token) === 0 ? 30 : 18) : 3;
        var occurrences = body.split(token).length - 1;
        if (occurrences) hit += Math.min(occurrences, 4);
        if (!hit) { ok = false; break; }
        score += hit;
      }
      if (ok) scored.push({ entry: entry, score: score });
    }
    scored.sort(function (a, b) { return b.score - a.score; });
    var perPage = {}, shown = [];
    for (var s = 0; s < scored.length && shown.length < 12; s++) {
      var url = scored[s].entry.u;
      perPage[url] = (perPage[url] || 0) + 1;
      if (perPage[url] <= 3) shown.push(scored[s].entry);
    }
    status.textContent = shown.length
      ? scored.length + (scored.length === 1 ? ' result' : ' results')
      : 'No results for "' + input.value.trim() + '"';
    list.innerHTML = shown.map(function (entry, i) {
      var href = root + entry.u + (entry.a ? '#' + entry.a : '');
      var crumb = entry.k + (entry.h ? ' · ' + escapeHtml(entry.p) : '');
      return '<li><a href="' + href + '"' + (i === 0 ? ' class="sel"' : '') + '>' +
        '<small>' + crumb + '</small><b>' + escapeHtml(entry.h || entry.p) + '</b>' +
        '<span>' + excerpt(entry.x, tokens) + '</span></a></li>';
    }).join('');
    list.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', closeSearch);
    });
  }

  var trigger = document.getElementById('search-trigger');
  if (trigger) trigger.addEventListener('click', openSearch);
  document.addEventListener('keydown', function (event) {
    var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName);
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      if (overlay && overlay.classList.contains('open')) closeSearch(); else openSearch();
    } else if (event.key === '/' && !typing) {
      event.preventDefault();
      openSearch();
    } else if (event.key === 'Escape') {
      closeSearch();
      setSidebar(false);
    }
  });
})();
