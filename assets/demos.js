/* Interactive Canvas demos for the three Example pages.
   Zero external dependencies; runs directly from file://. */
(function () {
  'use strict';

  function clamp(v, lo, hi) {
    return v < lo ? lo : v > hi ? hi : v;
  }

  function setupCanvas(canvas, w, h) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    return ctx;
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function attachDrag(view, axis, handlers) {
    let active = false;
    let startPos = 0;
    let lastPos = 0;
    let moved = false;
    const samples = [];

    function posOf(e) {
      return axis === 'x' ? e.clientX : e.clientY;
    }

    view.addEventListener('pointerdown', function (e) {
      active = true;
      moved = false;
      startPos = lastPos = posOf(e);
      samples.length = 0;
      samples.push({ t: performance.now(), p: lastPos });
      view.classList.add('dragging');
      view.setPointerCapture(e.pointerId);
      if (handlers.onDown) handlers.onDown(e);
    });

    view.addEventListener('pointermove', function (e) {
      if (!active) return;
      const p = posOf(e);
      const delta = p - lastPos;
      if (Math.abs(p - startPos) > 4) moved = true;
      lastPos = p;
      const now = performance.now();
      samples.push({ t: now, p: p });
      while (samples.length > 6 && now - samples[0].t > 100) samples.shift();
      if (delta !== 0 && handlers.onDelta) handlers.onDelta(delta);
    });

    function end(e) {
      if (!active) return;
      active = false;
      view.classList.remove('dragging');
      const now = performance.now();
      while (samples.length > 1 && now - samples[0].t > 120) samples.shift();
      let velocity = 0;
      if (samples.length >= 2) {
        const dt = (samples[samples.length - 1].t - samples[0].t) / 1000;
        if (dt > 0.004) {
          // Negate pointer velocity because dragging left/up (-dp) increases scroll pixels.
          velocity = -(samples[samples.length - 1].p - samples[0].p) / dt;
        }
      }
      if (!moved && handlers.onTap) {
        const rect = view.getBoundingClientRect();
        handlers.onTap(e.clientX - rect.left, e.clientY - rect.top);
      }
      if (handlers.onUp) handlers.onUp(velocity);
    }

    view.addEventListener('pointerup', end);
    view.addEventListener('pointercancel', end);

    view.addEventListener('wheel', function (e) {
      e.preventDefault();
      const raw = axis === 'x' ? (Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY) : e.deltaY;
      if (handlers.onWheel) handlers.onWheel(raw);
    }, { passive: false });
  }

  // ── Demo 1: SnapScrollPhysics ─────────────────────────────────
  function initSnapping(root) {
    const W = 320, H = 180;
    const ITEM = 160;
    const COUNT = 10;
    const MAX = ITEM * COUNT - W;
    const TOL_V = 45; // velocity tolerance in px/s

    const view = root.querySelector('.demo-view');
    const canvas = view.querySelector('canvas');
    const ctx = setupCanvas(canvas, W, H);

    let pixels = 0;
    let velocity = 0;
    let activity = 'idle';
    let snapEnabled = true;
    let target = 0;
    let raf = 0;
    let lastT = 0;

    const elPixels = root.querySelector('[data-f="pixels"]');
    const elVel = root.querySelector('[data-f="velocity"]');
    const elAct = root.querySelector('[data-f="activity"]');
    const elItem = root.querySelector('[data-f="item"]');
    const elTarget = root.querySelector('[data-f="target"]');

    function computeTarget(px, vel) {
      let item = px / ITEM;
      if (vel < -TOL_V) item -= 0.5;
      else if (vel > TOL_V) item += 0.5;
      return clamp(Math.round(item) * ITEM, 0, MAX);
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#0c0c0c';
      ctx.fillRect(0, 0, W, H);

      // Snap grid markers at top
      for (let i = 0; i < COUNT; i++) {
        const sx = i * ITEM - pixels + 8;
        if (sx < -ITEM || sx > W + ITEM) continue;
        const w = ITEM - 16;
        const t = i / (COUNT - 1);
        const r = Math.round(91 + (122 - 91) * t);
        const g = Math.round(141 + (77 - 141) * t);
        const b = Math.round(238 + (240 - 238) * t);
        ctx.fillStyle = 'rgb(' + r + ',' + g + ',' + b + ')';
        roundRect(ctx, sx, 22, w, H - 44, 14);
        ctx.fill();

        ctx.fillStyle = '#ffffff';
        ctx.font = '600 28px Inter, -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(i), sx + w / 2, H / 2);
      }

      // Leading edge snap indicator
      ctx.strokeStyle = 'rgba(255,255,255,0.35)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(8, 6);
      ctx.lineTo(8, 15);
      ctx.stroke();

      elPixels.textContent = pixels.toFixed(1);
      elVel.textContent = velocity.toFixed(0) + ' px/s';
      elAct.textContent = activity;
      elItem.textContent = (pixels / ITEM).toFixed(2);
      elTarget.textContent = snapEnabled ? target.toFixed(1) : '—';
    }

    function stopAnim() {
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
    }

    function startBallistic(v0) {
      stopAnim();
      velocity = v0;
      if (snapEnabled) {
        target = computeTarget(pixels, velocity);
        if (Math.abs(target - pixels) < 0.4 && Math.abs(velocity) < 5) {
          pixels = target;
          velocity = 0;
          activity = 'idle';
          draw();
          return;
        }
      } else if (Math.abs(velocity) < 8) {
        velocity = 0;
        activity = 'idle';
        draw();
        return;
      }
      activity = 'ballistic';
      lastT = performance.now();

      function step(now) {
        const dt = Math.min((now - lastT) / 1000, 0.032);
        lastT = now;
        if (snapEnabled) {
          // Overdamped/critically-damped spring matching Flutter's default ScrollPhysics.spring
          const k = 180;
          const c = 26;
          const x = pixels - target;
          const acc = -k * x - c * velocity;
          velocity += acc * dt;
          pixels += velocity * dt;
          if (Math.abs(pixels - target) < 0.35 && Math.abs(velocity) < 4) {
            pixels = target;
            velocity = 0;
            activity = 'idle';
            raf = 0;
            draw();
            return;
          }
        } else {
          // Clamping friction deceleration
          pixels += velocity * dt;
          velocity *= Math.pow(0.135, dt);
          if (pixels <= 0) { pixels = 0; velocity = 0; }
          if (pixels >= MAX) { pixels = MAX; velocity = 0; }
          if (Math.abs(velocity) < 6) {
            velocity = 0;
            activity = 'idle';
            raf = 0;
            draw();
            return;
          }
        }
        draw();
        raf = requestAnimationFrame(step);
      }
      raf = requestAnimationFrame(step);
    }

    let wheelTimer = 0;
    attachDrag(view, 'x', {
      onDown: function () {
        stopAnim();
        velocity = 0;
        activity = 'hold';
        draw();
      },
      onDelta: function (dx) {
        activity = 'drag';
        pixels = clamp(pixels - dx, 0, MAX);
        target = computeTarget(pixels, 0);
        draw();
      },
      onUp: function (vel) {
        startBallistic(vel);
      },
      onWheel: function (delta) {
        stopAnim();
        activity = 'drag';
        pixels = clamp(pixels + delta * 0.7, 0, MAX);
        target = computeTarget(pixels, 0);
        draw();
        clearTimeout(wheelTimer);
        wheelTimer = setTimeout(function () { startBallistic(0); }, 140);
      }
    });

    root.querySelectorAll('[data-mode]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        snapEnabled = btn.getAttribute('data-mode') === 'snap';
        root.querySelectorAll('[data-mode]').forEach(function (b) {
          b.classList.toggle('on', b === btn);
        });
        startBallistic(0);
      });
    });

    const flingBtn = root.querySelector('[data-action="fling"]');
    if (flingBtn) {
      flingBtn.addEventListener('click', function () {
        if (pixels >= MAX - 2) pixels = 0;
        startBallistic(520);
      });
    }

    draw();
  }

  // ── Demo 2: BareViewport ──────────────────────────────────────
  function initViewport(root) {
    const W = 260, H = 250;
    const WIN_X = 30, WIN_Y = 36, WIN_W = 200, WIN_H = 178;
    const ROW_H = 42, ROWS = 10;
    const CHILD_H = ROW_H * ROWS;
    const MAX = CHILD_H - WIN_H;

    const view = root.querySelector('.demo-view');
    const canvas = view.querySelector('canvas');
    const ctx = setupCanvas(canvas, W, H);

    let pixels = 84;
    let clipOn = true;
    let lastHit = 2;

    const elPixels = root.querySelector('[data-f="pixels"]');
    const elPaint = root.querySelector('[data-f="paintOffset"]');
    const elDim = root.querySelector('[data-f="viewportDim"]');
    const elMax = root.querySelector('[data-f="maxExtent"]');
    const elHit = root.querySelector('[data-f="hit"]');

    function drawRows(alpha) {
      ctx.save();
      ctx.globalAlpha = alpha;
      for (let i = 0; i < ROWS; i++) {
        const ry = WIN_Y - pixels + i * ROW_H;
        if (ry + ROW_H < -10 || ry > H + 10) continue;
        const hot = i === lastHit;
        ctx.fillStyle = hot ? 'rgba(91,141,238,0.28)' : '#1a1a1a';
        ctx.strokeStyle = hot ? '#82acf3' : 'rgba(255,255,255,0.09)';
        ctx.lineWidth = 1;
        roundRect(ctx, WIN_X + 10, ry + 4, WIN_W - 20, ROW_H - 8, 7);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = hot ? '#ffffff' : '#bdbdbd';
        ctx.font = '500 12px "JetBrains Mono", monospace';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText('Item ' + i + '  (y=' + (i * ROW_H) + ')', WIN_X + 22, ry + ROW_H / 2);
      }
      ctx.restore();
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#0c0c0c';
      ctx.fillRect(0, 0, W, H);

      if (!clipOn) {
        drawRows(0.28);
      }

      ctx.save();
      roundRect(ctx, WIN_X, WIN_Y, WIN_W, WIN_H, 10);
      ctx.clip();
      ctx.fillStyle = '#11131a';
      ctx.fillRect(WIN_X, WIN_Y, WIN_W, WIN_H);
      drawRows(1.0);
      ctx.restore();

      // Viewport border
      ctx.strokeStyle = '#82acf3';
      ctx.lineWidth = 2;
      roundRect(ctx, WIN_X, WIN_Y, WIN_W, WIN_H, 10);
      ctx.stroke();

      ctx.fillStyle = '#82acf3';
      ctx.font = '500 10px "JetBrains Mono", monospace';
      ctx.textAlign = 'left';
      ctx.fillText('BareViewport (178px)', WIN_X + 4, WIN_Y - 10);

      elPixels.textContent = pixels.toFixed(1);
      elPaint.textContent = '(0.0, ' + (-pixels).toFixed(1) + ')';
      elDim.textContent = WIN_H.toFixed(1);
      elMax.textContent = MAX.toFixed(1);
      elHit.textContent = lastHit === null ? 'outside' : 'Item ' + lastHit;
    }

    attachDrag(view, 'y', {
      onDelta: function (dy) {
        pixels = clamp(pixels - dy, 0, MAX);
        draw();
      },
      onWheel: function (dy) {
        pixels = clamp(pixels + dy * 0.6, 0, MAX);
        draw();
      },
      onTap: function (x, y) {
        if (x < WIN_X || x > WIN_X + WIN_W || y < WIN_Y || y > WIN_Y + WIN_H) {
          lastHit = null;
        } else {
          // Exact transform in hitTestChildren: localY - paintOffset.dy == localY + pixels
          const childY = (y - WIN_Y) + pixels;
          const idx = Math.floor(childY / ROW_H);
          lastHit = idx >= 0 && idx < ROWS ? idx : null;
        }
        draw();
      }
    });

    const clipBtn = root.querySelector('[data-action="toggle-clip"]');
    if (clipBtn) {
      clipBtn.addEventListener('click', function () {
        clipOn = !clipOn;
        clipBtn.classList.toggle('on', clipOn);
        clipBtn.textContent = clipOn ? 'ClipRect: on' : 'ClipRect: off (peek)';
        draw();
      });
    }

    draw();
  }

  // ── Demo 3: StickyHeader sliver ───────────────────────────────
  function initSticky(root) {
    const W = 260, H = 250;
    const BANNER_H = 96;
    const HEADER_H = 44;
    const ROW_H = 38, ROWS = 16;
    const TOTAL = BANNER_H + HEADER_H + ROW_H * ROWS;
    const MAX = TOTAL - H;

    const view = root.querySelector('.demo-view');
    const canvas = view.querySelector('canvas');
    const ctx = setupCanvas(canvas, W, H);

    let pixels = 0;

    const elScroll = root.querySelector('[data-f="scrollOffset"]');
    const elRem = root.querySelector('[data-f="remaining"]');
    const elScrollExt = root.querySelector('[data-f="scrollExtent"]');
    const elPaintExt = root.querySelector('[data-f="paintExtent"]');
    const elLayoutExt = root.querySelector('[data-f="layoutExtent"]');

    function draw() {
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#0c0c0c';
      ctx.fillRect(0, 0, W, H);

      // Sliver 1: SliverToBoxAdapter (96px banner)
      const s1Scroll = pixels;
      const s1Layout = clamp(BANNER_H - s1Scroll, 0, H);
      if (s1Layout > 0) {
        const y1 = -s1Scroll;
        ctx.fillStyle = '#181b24';
        ctx.fillRect(0, y1, W, BANNER_H);
        ctx.fillStyle = '#9aa4b8';
        ctx.font = '500 13px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Scrolls away (96px)', W / 2, y1 + BANNER_H / 2);
      }

      // Sliver 2: StickyHeader (preceding = 96px)
      const s2Scroll = Math.max(0, pixels - BANNER_H);
      const s2Rem = H - s1Layout;
      const s2Layout = clamp(HEADER_H - s2Scroll, 0, s2Rem);
      const s2Paint = Math.min(HEADER_H, s2Rem);
      const headerTop = s1Layout;

      // Sliver 3: SliverList starts at s1Layout + s2Layout!
      // When s2Scroll > 0, rows start above headerTop + HEADER_H and slide underneath.
      const listStartInContent = BANNER_H + HEADER_H;
      for (let i = 0; i < ROWS; i++) {
        const rowY = listStartInContent + i * ROW_H - pixels;
        if (rowY + ROW_H < 0 || rowY > H) continue;
        ctx.fillStyle = i % 2 === 0 ? '#121212' : '#161616';
        ctx.fillRect(0, rowY, W, ROW_H);
        ctx.fillStyle = '#9a9a9a';
        ctx.font = '400 12px "JetBrains Mono", monospace';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText('Row ' + i, 16, rowY + ROW_H / 2);
      }

      // Paint StickyHeader on top of rows when pinned
      if (s2Paint > 0) {
        if (s2Scroll > 0) {
          ctx.fillStyle = 'rgba(0,0,0,0.45)';
          ctx.fillRect(0, headerTop + s2Paint, W, 8);
        }
        ctx.fillStyle = '#12a6ad';
        ctx.fillRect(0, headerTop, W, s2Paint);
        ctx.fillStyle = '#ffffff';
        ctx.font = '600 13px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText('Sticks (44px)', 16, headerTop + s2Paint / 2);

        // Visual indicator for layoutExtent portion
        if (s2Layout < s2Paint) {
          ctx.fillStyle = 'rgba(255,255,255,0.8)';
          ctx.font = '500 10px "JetBrains Mono", monospace';
          ctx.textAlign = 'right';
          ctx.fillText(s2Layout === 0 ? 'pinned' : 'shrinking layoutExtent', W - 12, headerTop + s2Paint / 2);
        }
      }

      elScroll.textContent = s2Scroll.toFixed(1);
      elRem.textContent = s2Rem.toFixed(1);
      elScrollExt.textContent = HEADER_H.toFixed(1);
      elPaintExt.textContent = s2Paint.toFixed(1);
      elLayoutExt.textContent = s2Layout.toFixed(1);
    }

    attachDrag(view, 'y', {
      onDelta: function (dy) {
        pixels = clamp(pixels - dy, 0, MAX);
        draw();
      },
      onWheel: function (dy) {
        pixels = clamp(pixels + dy * 0.6, 0, MAX);
        draw();
      }
    });

    root.querySelectorAll('[data-jump]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        pixels = clamp( parseFloat(btn.getAttribute('data-jump')), 0, MAX );
        draw();
      });
    });

    draw();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-demo="snapping"]').forEach(initSnapping);
    document.querySelectorAll('[data-demo="viewport"]').forEach(initViewport);
    document.querySelectorAll('[data-demo="sticky"]').forEach(initSticky);
  });
})();
