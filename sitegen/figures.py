"""Inline SVG artwork: brand marks, example card art, and guide diagrams.

Everything is generated here so the site has no binary image assets and all
diagrams share one visual language (thin lines, mono labels, one accent).
"""

from __future__ import annotations

from typing import Callable

REGISTRY: dict[str, Callable[[], str]] = {}

ACCENT = '#5b8dee'
ACCENT_LIGHT = '#82acf3'
INK = '#ececec'
DIM = '#8a8a8a'
MUTED = '#4a4a4a'
LINE = '#333333'
PANEL = '#0e0e0e'
BLOCK = '#191919'
BLOCK_LINE = '#2c2c2c'
MONO = "'JetBrains Mono', ui-monospace, Menlo, monospace"


def figure(name: str):
    def register(fn: Callable[[], str]) -> Callable[[], str]:
        REGISTRY[name] = fn
        return fn

    return register


# ── tiny SVG helpers ──────────────────────────────────────────────

def svg(width: int, height: int, body: str, *, label: str = '', defs: str = '') -> str:
    aria = f' role="img" aria-label="{label}"' if label else ' aria-hidden="true"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}"{aria}>'
        f'{"<defs>" + defs + "</defs>" if defs else ""}{body}</svg>'
    )


def rect(x, y, w, h, *, r=0, fill='none', stroke='none', sw=1.0, extra='') -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}" {extra}/>'
    )


def line(x1, y1, x2, y2, *, stroke=LINE, sw=1.0, dash='', extra='') -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ''
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
        f'stroke-width="{sw}"{d} stroke-linecap="round" {extra}/>'
    )


def text(x, y, content, *, size=12, fill=DIM, anchor='start', weight=400, family=MONO, extra='') -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}" {extra}>{content}</text>'
    )


def arrow_v(x, y1, y2, *, stroke=DIM, sw=1.2, heads='both') -> str:
    """Vertical dimension arrow from y1 to y2 (y1 < y2)."""
    a = 4
    parts = [line(x, y1, x, y2, stroke=stroke, sw=sw)]
    if heads in ('both', 'start'):
        parts.append(f'<path d="M{x - a} {y1 + a} L{x} {y1} L{x + a} {y1 + a}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')
    if heads in ('both', 'end'):
        parts.append(f'<path d="M{x - a} {y2 - a} L{x} {y2} L{x + a} {y2 - a}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')
    return ''.join(parts)


def arrow_h(x1, x2, y, *, stroke=DIM, sw=1.2, heads='end') -> str:
    a = 4
    parts = [line(x1, y, x2, y, stroke=stroke, sw=sw)]
    if heads in ('both', 'end'):
        parts.append(f'<path d="M{x2 - a} {y - a} L{x2} {y} L{x2 - a} {y + a}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')
    if heads in ('both', 'start'):
        parts.append(f'<path d="M{x1 + a} {y - a} L{x1} {y} L{x1 + a} {y + a}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')
    return ''.join(parts)


def panel(width: int, height: int) -> str:
    return rect(0.5, 0.5, width - 1, height - 1, r=10, fill=PANEL, stroke='rgba(255,255,255,0.07)')


# ── brand ─────────────────────────────────────────────────────────

def _mark(size: int = 24) -> str:
    body = (
        f'<rect x="7.5" y="0.8" width="9" height="2.4" rx="1.2" fill="{ACCENT}" opacity="0.35"/>'
        f'<rect x="7.5" y="20.8" width="9" height="2.4" rx="1.2" fill="{ACCENT}" opacity="0.35"/>'
        f'<rect x="3.9" y="5.9" width="16.2" height="12.2" rx="3.2" fill="rgba(91,141,238,0.10)" stroke="{ACCENT_LIGHT}" stroke-width="1.8"/>'
        f'<rect x="7.5" y="8.9" width="9" height="2.4" rx="1.2" fill="{INK}"/>'
        f'<rect x="7.5" y="12.9" width="9" height="2.4" rx="1.2" fill="{ACCENT_LIGHT}"/>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size}" height="{size}">{body}</svg>'
    )


def _favicon() -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="7" fill="#0a0a0a"/>'
        f'<rect x="11" y="3.4" width="10" height="2.8" rx="1.4" fill="{ACCENT}" opacity="0.4"/>'
        f'<rect x="11" y="25.8" width="10" height="2.8" rx="1.4" fill="{ACCENT}" opacity="0.4"/>'
        f'<rect x="6" y="9" width="20" height="14" rx="4" fill="rgba(91,141,238,0.12)" stroke="{ACCENT_LIGHT}" stroke-width="2"/>'
        f'<rect x="11" y="12.4" width="10" height="2.8" rx="1.4" fill="{INK}"/>'
        f'<rect x="11" y="16.8" width="10" height="2.8" rx="1.4" fill="{ACCENT_LIGHT}"/>'
        '</svg>'
    )


def _logo_big() -> str:
    w, h = 240, 264
    defs = (
        '<linearGradient id="lb-a" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#9cc0ff"/><stop offset="1" stop-color="#4f7fe6"/></linearGradient>'
        '<linearGradient id="lb-b" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#b69cff"/><stop offset="1" stop-color="#6f56e8"/></linearGradient>'
        '<linearGradient id="lb-c" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#7fe0f5"/><stop offset="1" stop-color="#2f9fd6"/></linearGradient>'
        '<linearGradient id="lb-frame" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#cfe0ff"/><stop offset="1" stop-color="#5b8dee"/></linearGradient>'
        '<linearGradient id="lb-fade" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.16" stop-color="#fff" stop-opacity="1"/>'
        '<stop offset="0.84" stop-color="#fff" stop-opacity="1"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="lb-mask"><rect width="{w}" height="{h}" fill="url(#lb-fade)"/></mask>'
        '<filter id="lb-glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="12"/></filter>'
    )

    def tile(y: float, grad: str, opacity: float = 1.0) -> str:
        return (
            f'<g opacity="{opacity}">'
            f'<rect x="62" y="{y}" width="116" height="42" rx="11" fill="url(#{grad})"/>'
            f'<circle cx="83" cy="{y + 21}" r="9" fill="#fff" opacity="0.92"/>'
            f'<rect x="100" y="{y + 12}" width="56" height="6" rx="3" fill="#fff" opacity="0.92"/>'
            f'<rect x="100" y="{y + 24}" width="38" height="6" rx="3" fill="#fff" opacity="0.55"/>'
            '</g>'
        )

    body = (
        f'<rect x="42" y="50" width="156" height="164" rx="26" fill="{ACCENT}" opacity="0.28" filter="url(#lb-glow)"/>'
        '<g mask="url(#lb-mask)">'
        + tile(-2, 'lb-c', 0.55)
        + tile(215, 'lb-c', 0.55)
        + '</g>'
        '<rect x="42" y="50" width="156" height="164" rx="26" fill="#0d1220" stroke="url(#lb-frame)" stroke-width="5"/>'
        + tile(59, 'lb-a')
        + tile(111, 'lb-b')
        + tile(163, 'lb-a')
        + '<rect x="186" y="96" width="4" height="46" rx="2" fill="#fff" opacity="0.5"/>'
    )
    return svg(w, h, body, defs=defs)


def brand_assets() -> dict[str, str]:
    return {'logo.svg': _mark(), 'favicon.svg': _favicon(), 'logo-big.svg': _logo_big()}


# ── example card art (square) ─────────────────────────────────────

def _art(bg_from: str, bg_to: str, body: str, uid: str) -> str:
    defs = (
        f'<linearGradient id="{uid}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{bg_from}"/><stop offset="1" stop-color="{bg_to}"/></linearGradient>'
    )
    return svg(300, 300, f'<rect width="300" height="300" fill="url(#{uid})"/>' + body, defs=defs)


@figure('art-snapping-physics')
def art_snapping() -> str:
    cards = ''
    for i, x in enumerate([-40, 95, 230]):
        solid = i == 1
        cards += rect(x, 92, 110, 116, r=14, fill='#ffffff' if solid else 'rgba(255,255,255,0.28)')
        if solid:
            cards += rect(x + 16, 110, 78, 50, r=8, fill='#3a6fdc', extra='opacity="0.9"')
            cards += rect(x + 16, 172, 60, 7, r=3.5, fill='#1a2b52')
            cards += rect(x + 16, 186, 38, 7, r=3.5, fill='#1a2b52', extra='opacity="0.5"')
    ticks = ''.join(
        line(x, 238, x, 250, stroke='#ffffff', sw=2.5 if x == 150 else 1.5, extra=f'opacity="{1 if x == 150 else 0.45}"')
        for x in (15, 150, 285)
    )
    guide = line(150, 64, 150, 82, stroke='#ffffff', sw=2.5)
    arc = (
        '<path d="M205 54 C 190 40, 168 40, 156 56" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>'
        '<path d="M156 46 L155 57 L166 56" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    return _art('#3f74e8', '#2748a8', cards + ticks + guide + arc, 'art-a')


@figure('art-minimal-viewport')
def art_viewport() -> str:
    sheet = rect(78, -30, 144, 360, r=12, fill='rgba(255,255,255,0.16)')
    rows = ''.join(
        rect(94, y, 112, 26, r=7, fill='rgba(255,255,255,0.30)') for y in (-14, 22, 58, 242, 278)
    )
    frame = rect(56, 92, 188, 134, r=18, fill='#1b1140', stroke='#ffffff', sw=4)
    inside = ''.join(rect(94, y, 112, 26, r=7, fill='#ffffff') for y in (104, 140, 176))
    inside += rect(94, 212, 112, 10, r=5, fill='#ffffff')
    clip = (
        '<clipPath id="art-b-clip"><rect x="58" y="94" width="184" height="130" rx="16"/></clipPath>'
    )
    dim = (
        line(266, 92, 266, 226, stroke='#fff', sw=2)
        + line(260, 92, 272, 92, stroke='#fff', sw=2)
        + line(260, 226, 272, 226, stroke='#fff', sw=2)
    )
    body = sheet + rows + frame + f'<g clip-path="url(#art-b-clip)">{inside}</g>' + dim
    art = _art('#7a4df0', '#3f2a9c', body, 'art-b')
    return art.replace('<defs>', '<defs>' + clip, 1)


@figure('art-sticky-header')
def art_sticky() -> str:
    frame = rect(60, 40, 180, 220, r=18, fill='#062a2c', stroke='#ffffff', sw=4)
    clip = '<clipPath id="art-c-clip"><rect x="62" y="42" width="176" height="216" rx="16"/></clipPath>'
    rows = ''.join(
        rect(76, y, 148, 30, r=8, fill='rgba(255,255,255,0.26)') for y in (70, 108, 146, 184, 222)
    )
    header = rect(62, 42, 176, 46, fill='#ffffff') + rect(78, 58, 84, 9, r=4.5, fill='#0b5f63') + rect(78, 72, 46, 6, r=3, fill='#0b5f63', extra='opacity="0.5"')
    pin = (
        '<circle cx="214" cy="65" r="9" fill="#0b8f95"/>'
        '<path d="M214 60 L214 70 M210 64 L214 60 L218 64" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    shadow = '<rect x="62" y="88" width="176" height="10" fill="#000" opacity="0.22"/>'
    body = frame + f'<g clip-path="url(#art-c-clip)">{rows}{shadow}{header}{pin}</g>'
    art = _art('#12a6ad', '#0a5f70', body, 'art-c')
    return art.replace('<defs>', '<defs>' + clip, 1)


# ── guide diagrams ────────────────────────────────────────────────

def _box(x, y, w, h, title: str, sub: str = '', *, accent: bool = False) -> str:
    fill = 'rgba(91,141,238,0.10)' if accent else BLOCK
    stroke = ACCENT_LIGHT if accent else BLOCK_LINE
    t_fill = ACCENT_LIGHT if accent else INK
    parts = [rect(x, y, w, h, r=8, fill=fill, stroke=stroke, sw=1.3 if accent else 1.0)]
    if sub:
        parts.append(text(x + w / 2, y + h / 2 - 4, title, size=12, fill=t_fill, anchor='middle', weight=600))
        parts.append(text(x + w / 2, y + h / 2 + 13, sub, size=10.5, fill=DIM, anchor='middle'))
    else:
        parts.append(text(x + w / 2, y + h / 2 + 4, title, size=12, fill=t_fill, anchor='middle', weight=600))
    return ''.join(parts)


@figure('four-pieces')
def fig_four_pieces() -> str:
    w, h = 680, 220
    parts = [
        panel(w, h),
        _box(28, 82, 134, 56, 'Scrollable', 'gestures'),
        arrow_h(166, 224, 110, stroke=ACCENT_LIGHT),
        text(195, 100, 'delta', size=10, fill=DIM, anchor='middle'),
        _box(228, 72, 184, 76, 'ScrollPosition', 'pixels = 180.0', accent=True),
        # Physics above/below or right
        _box(248, 16, 144, 36, 'ScrollPhysics'),
        arrow_v(320, 54, 70, stroke=DIM, heads='both'),
        text(330, 65, 'clamps / sims', size=9.5, fill=DIM),
        arrow_h(416, 488, 110, stroke=ACCENT_LIGHT),
        text(452, 100, 'offset', size=10, fill=DIM, anchor='middle'),
        _box(492, 82, 160, 56, 'Viewport', 'paints slivers'),
        # Dimension feedback arc from Viewport back to ScrollPosition
        '<path d="M572 142 L572 184 L320 184 L320 152" fill="none" stroke="#4a4a4a" stroke-width="1.1" stroke-dasharray="3 3"/>',
        '<path d="M316 156 L320 150 L324 156" fill="none" stroke="#4a4a4a" stroke-width="1.1" stroke-linecap="round"/>',
        text(446, 198, 'applyViewportDimension / applyContentDimensions', size=9.5, fill=DIM, anchor='middle'),
    ]
    return svg(w, h, ''.join(parts), label='Scrollable, ScrollPosition, ScrollPhysics, and Viewport sharing one pixels offset')


@figure('scroll-extents')
def fig_scroll_extents() -> str:
    w, h = 680, 260
    # Content strip at x=230..410, y=22..238 (total 216px representing 960px)
    # Viewport window at y=68..146 (78px representing 300px)
    parts = [
        panel(w, h),
        # Full content strip
        rect(240, 24, 168, 212, r=7, fill=BLOCK, stroke=BLOCK_LINE),
        # Subtle row ticks inside content
        ''.join(rect(252, y, 144, 16, r=4, fill='#222222') for y in range(32, 228, 22)),
        # Viewport frame
        rect(232, 68, 184, 84, r=9, fill='rgba(91,141,238,0.09)', stroke=ACCENT_LIGHT, sw=1.8),
        text(324, 114, 'Viewport (300px)', size=11, fill=INK, anchor='middle', weight=600),
        # Left annotations: extentBefore, extentInside, extentAfter
        arrow_v(208, 24, 68, stroke=ACCENT_LIGHT),
        text(198, 50, 'extentBefore = 180', size=10.5, fill=ACCENT_LIGHT, anchor='end'),
        text(198, 63, '(pixels)', size=9.5, fill=DIM, anchor='end'),
        arrow_v(208, 70, 150, stroke=INK),
        text(198, 114, 'extentInside = 300', size=10.5, fill=INK, anchor='end'),
        arrow_v(208, 152, 236, stroke=DIM),
        text(198, 198, 'extentAfter = 480', size=10.5, fill=DIM, anchor='end'),
        # Right annotations: 0.0, maxScrollExtent, total content
        line(416, 24, 434, 24, stroke=MUTED),
        text(442, 28, 'minScrollExtent = 0.0', size=10.5, fill=DIM),
        line(416, 152, 434, 152, stroke=ACCENT_LIGHT, dash='3 3'),
        text(442, 156, 'maxScrollExtent = 660.0', size=10.5, fill=ACCENT_LIGHT),
        text(442, 170, '(960 content - 300 viewport)', size=9.5, fill=DIM),
        line(416, 236, 434, 236, stroke=MUTED),
        text(442, 240, 'content end = 960.0', size=10.5, fill=DIM),
    ]
    return svg(w, h, ''.join(parts), label='ScrollMetrics extents: extentBefore (pixels), extentInside (viewportDimension), and extentAfter')


@figure('physics-chain')
def fig_physics_chain() -> str:
    w, h = 680, 132
    parts = [
        panel(w, h),
        text(28, 30, 'physics.applyTo(ancestor) builds an immutable parent chain — outer link runs first:', size=10.5, fill=DIM),
        _box(28, 50, 186, 56, 'SnapScrollPhysics', 'widget physics', accent=True),
        arrow_h(218, 252, 78, stroke=ACCENT_LIGHT),
        text(235, 69, 'parent', size=9.5, fill=DIM, anchor='middle'),
        _box(256, 50, 190, 56, 'BouncingScrollPhysics', 'ScrollBehavior default'),
        arrow_h(450, 484, 78, stroke=DIM),
        text(467, 69, 'parent', size=9.5, fill=DIM, anchor='middle'),
        _box(488, 50, 164, 56, 'RangeMaintaining', 'resize guard'),
    ]
    return svg(w, h, ''.join(parts), label='ScrollPhysics linked parent chain')


@figure('activity-states')
def fig_activity_states() -> str:
    w, h = 680, 190
    parts = [
        panel(w, h),
        _box(26, 46, 108, 48, 'Idle', 'velocity = 0'),
        arrow_h(138, 178, 70, stroke=DIM),
        text(158, 61, 'down', size=9.5, fill=DIM, anchor='middle'),
        _box(182, 46, 108, 48, 'Hold', 'finger rests'),
        arrow_h(294, 334, 70, stroke=ACCENT_LIGHT),
        text(314, 61, 'move', size=9.5, fill=ACCENT_LIGHT, anchor='middle'),
        _box(338, 46, 122, 48, 'Drag', 'setPixels(-delta)', accent=True),
        arrow_h(464, 508, 70, stroke=ACCENT_LIGHT),
        text(486, 61, 'up', size=9.5, fill=ACCENT_LIGHT, anchor='middle'),
        _box(512, 46, 142, 48, 'Ballistic', 'Simulation tick', accent=True),
        # Return arc from Ballistic to Idle
        '<path d="M583 44 L583 20 L80 20 L80 42" fill="none" stroke="#4a4a4a" stroke-width="1.1"/>',
        '<path d="M76 38 L80 44 L84 38" fill="none" stroke="#4a4a4a" stroke-width="1.1" stroke-linecap="round"/>',
        text(332, 15, 'simulation done or null -> goIdle()', size=9.5, fill=DIM, anchor='middle'),
        # Driven activity below
        _box(264, 124, 152, 46, 'Driven', 'animateTo(curve)'),
        '<path d="M80 96 L80 147 L260 147" fill="none" stroke="#4a4a4a" stroke-width="1.1" stroke-dasharray="3 3"/>',
        '<path d="M256 143 L262 147 L256 151" fill="none" stroke="#4a4a4a" stroke-width="1.1" stroke-linecap="round"/>',
        text(170, 140, 'animateTo()', size=9.5, fill=DIM, anchor='middle'),
        '<path d="M418 147 L583 147 L583 98" fill="none" stroke="#4a4a4a" stroke-width="1.1" stroke-dasharray="3 3"/>',
        '<path d="M579 102 L583 96 L587 102" fill="none" stroke="#4a4a4a" stroke-width="1.1" stroke-linecap="round"/>',
        text(500, 140, 'goBallistic(0)', size=9.5, fill=DIM, anchor='middle'),
    ]
    return svg(w, h, ''.join(parts), label='ScrollActivity transitions between Idle, Hold, Drag, Ballistic, and Driven')


@figure('sliver-protocol')
def fig_sliver_protocol() -> str:
    w, h = 680, 210
    parts = [
        panel(w, h),
        _box(30, 56, 168, 96, 'RenderViewport', 'walks slivers in order'),
        # Down/right arrow: SliverConstraints
        arrow_h(204, 462, 78, stroke=ACCENT_LIGHT),
        rect(236, 50, 194, 22, r=4, fill='#141c2c'),
        text(333, 65, 'SliverConstraints  ->', size=10.5, fill=ACCENT_LIGHT, anchor='middle', weight=600),
        text(333, 95, 'scrollOffset, overlap, remainingPaintExtent', size=9.5, fill=DIM, anchor='middle'),
        # Left arrow: SliverGeometry
        arrow_h(462, 204, 130, stroke=INK, heads='start'),
        rect(236, 136, 194, 22, r=4, fill='#1b1b1b'),
        text(333, 151, '<-  SliverGeometry', size=10.5, fill=INK, anchor='middle', weight=600),
        text(333, 174, 'scrollExtent, paintExtent, layoutExtent', size=9.5, fill=DIM, anchor='middle'),
        _box(468, 56, 182, 96, 'RenderSliver', 'performLayout()', accent=True),
    ]
    return svg(w, h, ''.join(parts), label='SliverConstraints passed in and SliverGeometry returned during sliver performLayout')


@figure('cache-extent')
def fig_cache_extent() -> str:
    w, h = 680, 184
    # Horizontal diagram showing scroll axis left-to-right for readability
    parts = [
        panel(w, h),
        text(340, 28, 'Main axis along a SliverList (items outside cache are garbage-collected)', size=10.5, fill=DIM, anchor='middle'),
        # Unmounted left
        rect(28, 60, 92, 54, r=6, fill='#131313', stroke='#262626', extra='stroke-dasharray="3 3"'),
        text(74, 91, 'unmounted', size=10, fill=MUTED, anchor='middle'),
        # Leading cache
        rect(126, 60, 114, 54, r=6, fill=BLOCK, stroke=BLOCK_LINE),
        text(183, 84, 'leading cache', size=10, fill=DIM, anchor='middle'),
        text(183, 99, '250px', size=9.5, fill=MUTED, anchor='middle'),
        # Visible viewport
        rect(246, 52, 188, 70, r=8, fill='rgba(91,141,238,0.11)', stroke=ACCENT_LIGHT, sw=1.8),
        text(340, 84, 'visible viewport', size=11.5, fill=INK, anchor='middle', weight=600),
        text(340, 101, 'paintExtent', size=10, fill=ACCENT_LIGHT, anchor='middle'),
        # Trailing cache
        rect(440, 60, 114, 54, r=6, fill=BLOCK, stroke=BLOCK_LINE),
        text(497, 84, 'trailing cache', size=10, fill=DIM, anchor='middle'),
        text(497, 99, '250px', size=9.5, fill=MUTED, anchor='middle'),
        # Unmounted right
        rect(560, 60, 92, 54, r=6, fill='#131313', stroke='#262626', extra='stroke-dasharray="3 3"'),
        text(606, 91, 'unmounted', size=10, fill=MUTED, anchor='middle'),
        # Dimension bar under leading+visible+trailing
        arrow_h(126, 554, 146, stroke=ACCENT_LIGHT, heads='both'),
        text(340, 165, 'remainingCacheExtent (keep-alive or mounted Element range)', size=10, fill=ACCENT_LIGHT, anchor='middle'),
    ]
    return svg(w, h, ''.join(parts), label='Viewport visible area flanked by leading and trailing cacheExtent regions')


@figure('nested-scroll')
def fig_nested_scroll() -> str:
    w, h = 680, 200
    parts = [
        panel(w, h),
        _box(26, 66, 178, 68, 'Coordinator', 'splits drag & fling', accent=True),
        arrow_h(208, 256, 82, stroke=ACCENT_LIGHT),
        text(232, 74, 'first', size=9.5, fill=ACCENT_LIGHT, anchor='middle'),
        _box(260, 26, 190, 64, 'Outer ScrollView', 'headerSliverBuilder'),
        arrow_h(208, 256, 118, stroke=DIM),
        text(232, 133, 'rest', size=9.5, fill=DIM, anchor='middle'),
        _box(260, 110, 190, 64, 'Inner Scrollable', 'body ListView / tabs'),
        # Overlap absorber -> injector bridge
        _box(486, 26, 168, 64, 'OverlapAbsorber', 'measures pinned'),
        arrow_v(570, 92, 108, stroke=ACCENT_LIGHT, heads='end'),
        _box(486, 110, 168, 64, 'OverlapInjector', 'pads inner top'),
        line(450, 58, 486, 58, stroke=BLOCK_LINE, dash='3 3'),
        line(450, 142, 486, 142, stroke=BLOCK_LINE, dash='3 3'),
    ]
    return svg(w, h, ''.join(parts), label='NestedScrollView coordinator splitting deltas between outer header slivers and inner scrollable body')

