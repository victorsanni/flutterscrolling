#!/usr/bin/env python3
"""Builds the Flutter Scrolling static site.

    python3 build.py          # writes ./site
    open site/index.html      # every link is relative, so file:// works

Content lives in ./content/<section>/<slug>.md (Markdown subset, see
sitegen/md.py). Navigation order is defined in NAV below. The build fails
loudly on broken internal links, missing pages, or unknown figures.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sitegen import figures
from sitegen.dart_highlight import highlight_dart
from sitegen.md import Heading, Renderer, esc, parse_front_matter

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / 'content'
STATIC = ROOT / 'static'
OUT = ROOT / 'site'

SITE = 'Flutter Scrolling'
TAGLINE = (
    "Learn how Flutter scrolling really works. Master the handful of pieces "
    "that turn a drag into moving pixels."
)

# Section -> label, kind (shown in search), sidebar groups in reading order.
NAV: dict[str, dict] = {
    'guides': {
        'label': 'Guides',
        'kind': 'Guide',
        'groups': [
            ('Guides', [
                'index', 'how-scrolling-works', 'scroll-position', 'scroll-physics',
                'scroll-activities', 'scroll-controllers', 'scroll-notifications',
                'scroll-behavior',
            ]),
            ('Slivers', [
                'viewports', 'sliver-layout', 'lazy-children', 'pinned-headers',
                'scroll-views',
            ]),
            ('Going Further', [
                'revealing-content', 'nested-scrolling', 'two-dimensional-scrolling',
            ]),
        ],
    },
    'api': {
        'label': 'API',
        'kind': 'API',
        'groups': [
            ('API', ['index']),
            ('Scroll Physics', [
                'apply-to', 'apply-physics-to-user-offset', 'apply-boundary-conditions',
                'create-ballistic-simulation',
            ]),
            ('Position and Controller', [
                'jump-to', 'animate-to', 'ensure-visible', 'create-scroll-position',
                'scroll-metrics',
            ]),
            ('Notifications', ['on-notification']),
            ('Slivers', [
                'sliver-constraints', 'sliver-geometry', 'sliver-perform-layout',
                'child-main-axis-position',
            ]),
            ('Scroll Behavior', ['get-scroll-physics']),
        ],
    },
    'examples': {
        'label': 'Examples',
        'kind': 'Example',
        'groups': [
            ('Examples', ['index', 'snapping-physics', 'minimal-viewport', 'sticky-header']),
        ],
    },
}

# Home page picks.
HOME_GUIDES = [
    ('guides', 'how-scrolling-works', 'flow', 'Read guide'),
    ('guides', 'scroll-position', 'position', 'Read guide'),
    ('guides', 'sliver-layout', 'sliver', 'Read guide'),
]
HOME_EXAMPLES = ['snapping-physics', 'minimal-viewport', 'sticky-header']
HOME_METHODS = [
    ('api', 'apply-boundary-conditions',
     'applyBoundaryConditions(ScrollMetrics position, double value)',
     'Decides how much of a proposed scroll offset is refused at the edges. '
     'Return 0.0 to let the content move freely.',
     'double — the overscroll to hand back; 0.0 accepts the whole move'),
    ('api', 'create-ballistic-simulation',
     'createBallisticSimulation(ScrollMetrics position, double velocity)',
     'Describes what the position does after the finger lifts: a fling, a spring back, '
     'a snap, or nothing at all.',
     'Simulation? — null means the position goes idle where it is'),
    ('api', 'sliver-perform-layout',
     'performLayout()',
     'Reads the SliverConstraints handed down by the viewport and answers with a '
     'SliverGeometry. Must set geometry before returning.',
     'void — called by the viewport once per sliver, per layout attempt'),
]
READING_PATH = [
    ('guides', 'how-scrolling-works'),
    ('guides', 'scroll-position'),
    ('guides', 'scroll-physics'),
    ('guides', 'scroll-activities'),
    ('guides', 'viewports'),
    ('guides', 'sliver-layout'),
]

ICONS = {
    'flow': '<path d="M3 5 L9 5"/><path d="M11 5 L17 5"/><path d="M3 10 L17 10"/>'
            '<path d="M3 15 L13 15"/><path d="M14 13 L17 15 L14 17"/>',
    'position': '<path d="M5 3 L15 3 L15 17 L5 17 Z"/><path d="M8 8 L12 8"/>'
                '<path d="M8 11 L12 11"/><path d="M10 5.2 L10 5.8"/>',
    'sliver': '<path d="M4 4 L16 4"/><path d="M4 8 L16 8"/><path d="M4 12 L16 12"/>'
              '<path d="M4 16 L11 16"/>',
    'path': '<path d="M5 4 L5 16"/><path d="M5 4 L13 4 L11 7 L13 10 L5 10"/>',
    'search': '<circle cx="7" cy="7" r="5"></circle><path d="M11 11 L14 14"></path>',
}


def icon(name: str, size: int = 20) -> str:
    return (
        f'<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round" width="{size}" height="{size}" '
        f'aria-hidden="true">{ICONS[name]}</svg>'
    )


@dataclass
class Page:
    section: str
    slug: str
    meta: dict[str, str]
    source: str
    html: str = ''
    headings: list[Heading] = field(default_factory=list)
    chunks: list[tuple[str, str]] = field(default_factory=list)
    words: int = 0

    @property
    def key(self) -> tuple[str, str]:
        return (self.section, self.slug)

    @property
    def out_rel(self) -> str:
        return f'{self.section}/{self.slug}.html'

    @property
    def title(self) -> str:
        return self.meta['title']

    @property
    def nav_title(self) -> str:
        return self.meta.get('nav', self.meta['title'])

    @property
    def description(self) -> str:
        return self.meta.get('description', '')


class BuildError(Exception):
    pass


class Site:
    def __init__(self) -> None:
        self.pages: dict[tuple[str, str], Page] = {}
        self.links: list[tuple[str, tuple[str, str] | None, str]] = []
        self.errors: list[str] = []

    # ── loading ───────────────────────────────────────────────────
    def load(self) -> None:
        for section, conf in NAV.items():
            for _, slugs in conf['groups']:
                for slug in slugs:
                    path = CONTENT / section / f'{slug}.md'
                    if not path.exists():
                        self.errors.append(f'missing content file: {path.relative_to(ROOT)}')
                        continue
                    meta, body = parse_front_matter(path.read_text(encoding='utf-8'))
                    if 'title' not in meta:
                        self.errors.append(f'{path.relative_to(ROOT)}: front matter needs a title')
                        continue
                    self.pages[(section, slug)] = Page(section, slug, meta, body)
        known = {CONTENT / s / f'{slug}.md' for (s, slug) in self.pages}
        for path in CONTENT.rglob('*.md'):
            if path not in known:
                self.errors.append(f'content file not in NAV: {path.relative_to(ROOT)}')

    # ── links ─────────────────────────────────────────────────────
    def resolver(self, page_rel: str):
        depth_prefix = '../' * page_rel.count('/')

        def resolve(url: str) -> str:
            if url.startswith('#'):
                self.links.append((page_rel, None, url[1:]))
                return url
            if not url.startswith('/'):
                self.errors.append(f'{page_rel}: link must be site-absolute or external: {url}')
                return url
            path, _, anchor = url.partition('#')
            parts = [p for p in path.split('/') if p]
            if not parts:
                target_rel, key = 'index.html', ('', 'home')
            elif len(parts) == 1:
                target_rel, key = f'{parts[0]}/index.html', (parts[0], 'index')
            else:
                target_rel, key = f'{parts[0]}/{parts[1]}.html', (parts[0], parts[1])
            self.links.append((page_rel, key, anchor))
            return depth_prefix + target_rel + (f'#{anchor}' if anchor else '')

        return resolve

    def check_links(self) -> None:
        by_rel = {p.out_rel: p for p in self.pages.values()}
        for page_rel, key, anchor in self.links:
            if key is None:
                target = by_rel.get(page_rel)
            elif key == ('', 'home'):
                if anchor:
                    self.errors.append(f'{page_rel}: anchors on the home page are not tracked')
                continue
            else:
                target = self.pages.get(key)
                if target is None:
                    self.errors.append(f'{page_rel}: link to missing page /{key[0]}/{key[1]}')
                    continue
            if anchor and target is not None:
                if anchor not in {h.id for h in target.headings}:
                    self.errors.append(
                        f'{page_rel}: link to missing anchor #{anchor} on {target.out_rel}'
                    )

    # ── rendering ─────────────────────────────────────────────────
    def figure(self, page_rel: str):
        def render(name: str, caption: str) -> str:
            fn = figures.REGISTRY.get(name)
            if fn is None:
                self.errors.append(f'{page_rel}: unknown figure {name}')
                return ''
            return fn()

        return render

    def render_pages(self) -> None:
        for page in self.pages.values():
            renderer = Renderer(self.resolver(page.out_rel), self.figure(page.out_rel))
            result = renderer.render(page.source)
            page.html = result.html
            page.headings = result.headings
            page.chunks = result.search_chunks
            page.words = result.word_count

    # ── chrome ────────────────────────────────────────────────────
    def head(self, title: str, description: str, root: str, scripts: list[str]) -> str:
        extra = ''.join(f'<script src="{root}assets/{s}" defer></script>' for s in scripts)
        return f'''<!DOCTYPE html>
<html lang="en" class="no-js">
<head>
<meta charset="utf-8">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/svg+xml" href="{root}assets/images/favicon.svg">
<link rel="preload" href="{root}assets/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{root}assets/site.css">
<script>document.documentElement.classList.remove('no-js');</script>
<script src="{root}assets/search-index.js" defer></script>
<script src="{root}assets/site.js" defer></script>
{extra}</head>
'''

    def navbar(self, root: str, active: str | None, has_sidebar: bool) -> str:
        links = ''.join(
            f'<li><a{" class=\"active\"" if active == section else ""} '
            f'href="{root}{section}/index.html">{conf["label"]}</a></li>'
            for section, conf in NAV.items()
        )
        toggle_class = 'navbar-toggle has-sidebar' if has_sidebar else 'navbar-toggle'
        return f'''<nav class="navbar">
<button class="{toggle_class}" id="sidebar-toggle" type="button" aria-label="Toggle navigation">
<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="18" y2="18"/></svg>
</button>
<a class="navbar-brand" href="{root}index.html"><img alt="" src="{root}assets/images/logo.svg"><span>{SITE}</span></a>
<div class="navbar-divider"></div>
<ul class="navbar-nav">{links}</ul>
<button class="navbar-search" id="search-trigger" type="button" aria-label="Search docs">
<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" aria-hidden="true">{ICONS['search']}</svg>
<span>Search docs...</span><span class="kbd">⌘K</span>
</button>
<a class="btn-nav" href="{root}guides/how-scrolling-works.html">Start here</a>
</nav>
'''

    def footer(self, root: str) -> str:
        links = ''.join(
            f'<a href="{root}{section}/index.html">{conf["label"]}</a>'
            for section, conf in NAV.items()
        )
        return f'''<footer class="site-footer">
<p>Unofficial study notes, checked against the Flutter source. Modelled on <a href="https://renderobjects.com" target="_blank" rel="noopener">renderobjects.com</a>.</p>
<nav>{links}</nav>
</footer>'''

    def sidebar(self, page: Page, root: str) -> str:
        groups = []
        for label, slugs in NAV[page.section]['groups']:
            items = []
            for slug in slugs:
                target = self.pages[(page.section, slug)]
                name = 'Overview' if slug == 'index' else target.nav_title
                cls = ' class="active"' if target.key == page.key else ''
                items.append(
                    f'<li><a{cls} href="{root}{target.out_rel}" title="{esc(name)}">{esc(name)}</a></li>'
                )
            groups.append(
                f'<div class="sidebar-group"><h3>{esc(label)}</h3><ul>{"".join(items)}</ul></div>'
            )
        return f'<nav class="sidebar" id="sidebar" aria-label="Section">{"".join(groups)}</nav>'

    def toc(self, page: Page) -> str:
        items = ''.join(
            f'<li{" class=\"sub\"" if h.level > 2 else ""}><a href="#{h.id}">{esc(h.text)}</a></li>'
            for h in page.headings
            if h.level <= 3
        )
        return f'<aside class="toc"><div><h3>On this page</h3><ul>{items}</ul></div></aside>'

    def next_link(self, page: Page, root: str) -> str:
        if page.section != 'guides':
            return ''
        order = [s for _, slugs in NAV['guides']['groups'] for s in slugs]
        idx = order.index(page.slug)
        if idx + 1 >= len(order):
            target, label = self.pages[('examples', 'index')], 'Next: see it in real code'
        else:
            target = self.pages[('guides', order[idx + 1])]
            label = 'Start here' if page.slug == 'index' else 'Next guide'
        return (
            f'<a class="next" href="{root}{target.out_rel}"><div><small>{label}</small>'
            f'<b>{esc(target.nav_title)}</b></div><span>→</span></a>'
        )

    def render_doc(self, page: Page) -> str:
        root = '../'
        scripts = [s.strip() for s in page.meta.get('scripts', '').split(',') if s.strip()]
        title = f'{page.title} | {SITE}'
        desc = f'<p>{esc(page.description)}</p>' if page.description else ''
        return (
            self.head(title, page.description, root, scripts)
            + f'<body data-root="{root}">\n'
            + self.navbar(root, page.section, True)
            + '<div class="docs">\n'
            + self.sidebar(page, root)
            + '<div class="sidebar-barrier" id="sidebar-barrier"></div>\n'
            + '<main class="docs-main"><div class="docs-row"><div class="docs-content">\n'
            + f'<header class="page-header"><h1>{esc(page.title)}</h1>{desc}</header>\n'
            + f'<section class="content">\n{page.html}\n</section>\n'
            + self.next_link(page, root)
            + f'<div class="docs-footer">{self.footer(root)}</div>\n'
            + '</div>\n'
            + self.toc(page)
            + '</div></main>\n</div>\n</body>\n</html>\n'
        )

    # ── home ──────────────────────────────────────────────────────
    def render_home(self) -> str:
        root = ''
        counts = {s: sum(len(g[1]) for g in c['groups']) - 1 for s, c in NAV.items()}
        hero_code = highlight_dart(HERO_CODE)

        guide_cards = ''.join(
            f'<a class="card reveal" href="{self.pages[(s, slug)].out_rel}">'
            f'<div class="card-icon">{icon(ic)}</div>'
            f'<div class="card-title">{esc(self.pages[(s, slug)].nav_title)}</div>'
            f'<p class="card-desc">{esc(self.pages[(s, slug)].meta.get("card", self.pages[(s, slug)].description))}</p>'
            f'<span class="card-link">{label} →</span></a>'
            for s, slug, ic, label in HOME_GUIDES
        )
        example_cards = ''.join(
            f'<a class="card reveal" href="{self.pages[("examples", slug)].out_rel}">'
            f'<div class="card-art">{figures.REGISTRY["art-" + slug]()}</div>'
            f'<div class="card-title">{esc(self.pages[("examples", slug)].nav_title)}</div>'
            f'<p class="card-desc">{esc(self.pages[("examples", slug)].meta.get("card", self.pages[("examples", slug)].description))}</p>'
            f'<span class="card-link">See example →</span></a>'
            for slug in HOME_EXAMPLES
        )
        methods = ''.join(
            f'<a class="method reveal" href="{self.pages[(s, slug)].out_rel}">'
            f'<div class="method-head"><b>{esc(sig)}</b><span>docs →</span></div>'
            f'<div class="method-body"><p>{esc(text)}</p><small>{esc(ret)}</small></div></a>'
            for s, slug, sig, text, ret in HOME_METHODS
        )
        steps = ''.join(
            f'<li><a href="{self.pages[k].out_rel}">{esc(self.pages[k].nav_title)}</a></li>'
            for k in READING_PATH
        )
        return (
            self.head(f"{SITE} — How Flutter turns a drag into moving pixels", TAGLINE, root, [])
            + f'<body data-root="{root}">\n'
            + self.navbar(root, None, False)
            + f'''<section class="hero"><div class="hero-inner">
<img class="hero-logo" alt="{SITE} logo" src="assets/images/logo-big.svg">
<div class="hero-eyebrow">Advanced Flutter</div>
<h1 class="hero-title">{SITE}</h1>
<p class="hero-tagline">{TAGLINE}</p>
<div class="code-panel"><div class="code-panel-header"><i></i><i></i><i></i><span>scroll_view.dart</span></div>
<pre>{hero_code}</pre></div>
</div></section>
<div class="stats">
<div><b>{counts['guides']}</b><span>guides</span></div>
<div><b>{counts['api']}</b><span>api docs</span></div>
<div><b>{counts['examples']}</b><span>examples</span></div>
<div><b>1</b><span>reading order</span></div>
</div>
<div class="section">
<div class="section-label">The what, why, and how</div>
<h2 class="section-heading">Scrolling Guides</h2>
<p class="section-sub">A scroll view looks like one widget. It is four small pieces passing one number around. Learn each piece on its own, in order, with our guides.</p>
<div class="cards">{guide_cards}</div>
<a class="more-link" href="guides/index.html">View all guides →</a>
</div>
<div class="band"><div class="section">
<div class="section-label">Examples</div>
<h2 class="section-heading">Real Code, Real Scrolling</h2>
<p class="section-sub">Ground your understanding with small, complete implementations you can drag around, including explanations of every decision.</p>
<div class="cards">{example_cards}</div>
<a class="more-link" href="examples/index.html">View all examples →</a>
</div></div>
<div class="section">
<div class="section-label">API Reference</div>
<h2 class="section-heading">Docs for Every Method</h2>
<p class="section-sub">Get help with the specific scrolling methods you override and call, with our API docs.</p>
<div class="methods">{methods}</div>
<a class="more-link" href="api/index.html">View full API reference →</a>
</div>
<div class="path-wrap"><div class="section">
<div class="section-label">Reading order</div>
<h2 class="section-heading">Learn It in One Sitting</h2>
<p class="section-sub">Six guides, read in order, cover the whole machine. Everything else on this site is detail you can look up later.</p>
<div class="path-card">
<div class="path-icon">{icon('path')}</div>
<div class="path-title">The short path</div>
<p class="path-desc">Start at the top. Each guide assumes only the ones before it.</p>
<ol class="path-steps">{steps}</ol>
<a class="btn" href="{self.pages[READING_PATH[0]].out_rel}">Start reading</a>
</div>
</div>
{self.footer(root)}
</div>
</body>
</html>
'''
        )

    # ── search index ──────────────────────────────────────────────
    def search_index(self) -> str:
        entries = []
        for page in self.pages.values():
            kind = NAV[page.section]['kind']
            headings = {h.id: h.text for h in page.headings}
            entries.append({
                'u': page.out_rel, 'a': '', 'p': page.title, 'h': '', 'k': kind,
                'x': page.description,
            })
            for hid, text in page.chunks:
                entries.append({
                    'u': page.out_rel, 'a': hid, 'p': page.title,
                    'h': headings.get(hid, ''), 'k': kind, 'x': text,
                })
        return 'window.SEARCH_INDEX = ' + json.dumps(entries, ensure_ascii=False) + ';\n'

    # ── output ────────────────────────────────────────────────────
    def write(self) -> None:
        if OUT.exists():
            shutil.rmtree(OUT)
        (OUT / 'assets').mkdir(parents=True)
        shutil.copytree(STATIC / 'fonts', OUT / 'assets' / 'fonts')
        (OUT / 'assets' / 'images').mkdir()
        for name, svg in figures.brand_assets().items():
            (OUT / 'assets' / 'images' / name).write_text(svg, encoding='utf-8')
        for name in ('site.css', 'site.js', 'demos.js'):
            src = STATIC / name
            if src.exists():
                shutil.copy(src, OUT / 'assets' / name)
        (OUT / '.nojekyll').write_text('', encoding='utf-8')
        (OUT / 'assets' / 'search-index.js').write_text(self.search_index(), encoding='utf-8')
        (OUT / 'index.html').write_text(self.render_home(), encoding='utf-8')
        for page in self.pages.values():
            target = OUT / page.out_rel
            target.parent.mkdir(exist_ok=True)
            target.write_text(self.render_doc(page), encoding='utf-8')

    def build(self) -> None:
        self.load()
        if not self.errors:
            self.render_pages()
            self.check_links()
        if self.errors:
            raise BuildError('\n'.join(f'  - {e}' for e in self.errors))
        self.write()


HERO_CODE = '''\
Scrollable(                         // turns gestures into a ScrollPosition
  controller: controller,           // lets you read and move the position
  physics: physics,                 // decides how the position may move
  viewportBuilder: (context, offset) {
    return Viewport(                // the window you look through
      offset: offset,               // the same ScrollPosition, one number
      slivers: [/**/],              // the content, laid out on demand
    );
  },
)'''


def main() -> int:
    site = Site()
    try:
        site.build()
    except BuildError as error:
        print('Build failed:\n' + str(error), file=sys.stderr)
        return 1
    total = sum(p.words for p in site.pages.values())
    for section in NAV:
        pages = [p for p in site.pages.values() if p.section == section]
        print(f'{section:9} {len(pages):2} pages  {sum(p.words for p in pages):6} words')
    print(f'built {len(site.pages) + 1} pages, {total} words -> {OUT}')
    print(f'open file://{OUT / "index.html"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
