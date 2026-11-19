"""A small Markdown subset to HTML converter, sized for this site.

Supported blocks: headings (## ### ####), paragraphs, fenced code, bullet and
numbered lists (nested via indentation), blockquotes, pipe tables, horizontal
rules, raw HTML blocks, and `{{figure:name|caption}}` directives.

Supported inline: `code`, **bold**, *italic*, [text](url).

Internal links are written site-absolute without an extension
(`/guides/scroll-position#some-heading`) and resolved by the caller.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Callable

from .dart_highlight import highlight_dart


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def slugify(text: str) -> str:
    text = re.sub(r'`', '', text).lower()
    text = re.sub(r'[^a-z0-9 \-]', '', text)
    return re.sub(r' ', '-', text.strip())


def strip_inline(text: str) -> str:
    """Plain text for a heading or paragraph (used for TOC and search)."""
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])', r'\1', text)
    return text


@dataclass
class Heading:
    level: int
    text: str  # plain text
    html: str  # inline-rendered
    id: str


@dataclass
class RenderResult:
    html: str = ''
    headings: list[Heading] = field(default_factory=list)
    # (heading id or '', plain text) chunks for the search index
    search_chunks: list[tuple[str, str]] = field(default_factory=list)
    word_count: int = 0


class Renderer:
    def __init__(
        self,
        resolve_link: Callable[[str], str],
        figure: Callable[[str, str], str],
    ) -> None:
        self.resolve_link = resolve_link
        self.figure = figure
        self.headings: list[Heading] = []
        self.chunks: list[tuple[str, list[str]]] = [('', [])]
        self._ids: dict[str, int] = {}

    # ── inline ────────────────────────────────────────────────────
    def inline(self, text: str) -> str:
        codes: list[str] = []

        def stash(match: re.Match[str]) -> str:
            codes.append('<code>' + esc(match.group(1)) + '</code>')
            return f'\x00{len(codes) - 1}\x00'

        text = re.sub(r'`([^`]+)`', stash, text)
        text = esc(text)

        def link(match: re.Match[str]) -> str:
            label, url = match.group(1), html.unescape(match.group(2))
            if re.match(r'^[a-z]+://', url):
                return f'<a href="{esc(url)}" target="_blank" rel="noopener">{label}</a>'
            return f'<a href="{esc(self.resolve_link(url))}">{label}</a>'

        text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])', r'<em>\1</em>', text)
        return re.sub(r'\x00(\d+)\x00', lambda m: codes[int(m.group(1))], text)

    def _note(self, text: str) -> None:
        self.chunks[-1][1].append(strip_inline(text))

    # ── blocks ────────────────────────────────────────────────────
    def render(self, source: str) -> RenderResult:
        body = self.blocks(source.split('\n'))
        chunks = [(hid, ' '.join(parts)) for hid, parts in self.chunks if parts]
        words = sum(len(text.split()) for _, text in chunks)
        return RenderResult(body, self.headings, chunks, words)

    def blocks(self, lines: list[str]) -> str:
        out: list[str] = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue

            # Fenced code
            fence = re.match(r'^```(\w*)\s*$', line)
            if fence:
                lang = fence.group(1)
                i += 1
                code: list[str] = []
                while i < n and not re.match(r'^```\s*$', lines[i]):
                    code.append(lines[i])
                    i += 1
                i += 1
                out.append(self.code_block('\n'.join(code), lang))
                continue

            # Heading
            heading = re.match(r'^(#{2,4}) +(.+?)\s*$', line)
            if heading:
                out.append(self.heading(len(heading.group(1)), heading.group(2)))
                i += 1
                continue

            # Horizontal rule
            if re.match(r'^-{3,}\s*$', line):
                out.append('<hr>')
                i += 1
                continue

            # Figure directive
            directive = re.match(r'^\{\{figure:([\w-]+)(?:\|(.*))?\}\}\s*$', line)
            if directive:
                caption = directive.group(2) or ''
                svg = self.figure(directive.group(1), caption)
                cap = f'<figcaption>{self.inline(caption)}</figcaption>' if caption else ''
                out.append(f'<figure class="figure">{svg}{cap}</figure>')
                if caption:
                    self._note(caption)
                i += 1
                continue

            # Raw HTML block (until blank line)
            if re.match(r'^<(div|figure|table|section|p|ul|ol|a|details)\b', line):
                raw: list[str] = []
                while i < n and lines[i].strip():
                    raw.append(lines[i])
                    i += 1
                out.append('\n'.join(raw))
                continue

            # Blockquote
            if line.startswith('>'):
                quote: list[str] = []
                while i < n and lines[i].startswith('>'):
                    quote.append(re.sub(r'^> ?', '', lines[i]))
                    i += 1
                out.append('<blockquote>' + self.blocks(quote) + '</blockquote>')
                continue

            # Table
            if line.lstrip().startswith('|') and i + 1 < n and re.match(r'^\s*\|[\s:|-]+\|\s*$', lines[i + 1]):
                rows: list[list[str]] = []
                while i < n and lines[i].lstrip().startswith('|'):
                    cells = [c.strip() for c in re.split(r'(?<!\\)\|', lines[i].strip().strip('|'))]
                    rows.append([c.replace('\\|', '|') for c in cells])
                    i += 1
                out.append(self.table(rows[0], rows[2:]))
                continue

            # Lists
            item = re.match(r'^( *)([-*]|\d+\.) +(.*)$', line)
            if item and len(item.group(1)) == 0:
                ordered = item.group(2)[0].isdigit()
                items: list[list[str]] = []
                while i < n:
                    m = re.match(r'^([-*]|\d+\.) +(.*)$', lines[i])
                    if m and (m.group(1)[0].isdigit() == ordered):
                        items.append([m.group(2)])
                        i += 1
                    elif items and (lines[i].startswith('  ') or not lines[i].strip()):
                        # continuation or blank line inside the list
                        if not lines[i].strip():
                            # blank line: list continues only if next non-blank is indented or an item
                            j = i
                            while j < n and not lines[j].strip():
                                j += 1
                            if j < n and (lines[j].startswith('  ') or re.match(r'^([-*]|\d+\.) +', lines[j])):
                                nxt = re.match(r'^([-*]|\d+\.) +', lines[j])
                                if nxt and (nxt.group(1)[0].isdigit() != ordered):
                                    break
                                items[-1].append('')
                                i += 1
                                continue
                            break
                        items[-1].append(re.sub(r'^ {2,4}', '', lines[i], count=1))
                        i += 1
                    else:
                        break
                tag = 'ol' if ordered else 'ul'
                rendered = ''.join('<li>' + self.list_item(it) + '</li>' for it in items)
                out.append(f'<{tag}>{rendered}</{tag}>')
                continue

            # Paragraph
            para: list[str] = []
            while i < n and lines[i].strip() and not self._starts_block(lines[i]):
                para.append(lines[i].strip())
                i += 1
            text = ' '.join(para)
            self._note(text)
            out.append('<p>' + self.inline(text) + '</p>')
        return '\n'.join(out)

    @staticmethod
    def _starts_block(line: str) -> bool:
        return bool(
            re.match(r'^(```|#{2,4} |>|\{\{figure:|-{3,}\s*$)', line)
            or re.match(r'^([-*]|\d+\.) +', line)
            or re.match(r'^\s*\|', line)
        )

    def list_item(self, lines: list[str]) -> str:
        while lines and not lines[-1].strip():
            lines = lines[:-1]
        simple = all(
            ln.strip() and not re.match(r'^(```|[-*] |\d+\. |>)', ln) for ln in lines
        )
        if simple:
            text = ' '.join(ln.strip() for ln in lines)
            self._note(text)
            return self.inline(text)
        # Leading text lines form an inline lead; the rest are nested blocks.
        lead: list[str] = []
        k = 0
        while k < len(lines) and lines[k].strip() and not re.match(r'^(```|[-*] |\d+\. |>)', lines[k]):
            lead.append(lines[k].strip())
            k += 1
        text = ' '.join(lead)
        if text:
            self._note(text)
        return self.inline(text) + self.blocks(lines[k:])

    def heading(self, level: int, text: str) -> str:
        plain = strip_inline(text)
        base = slugify(text) or 'section'
        count = self._ids.get(base, 0)
        self._ids[base] = count + 1
        hid = base if count == 0 else f'{base}-{count + 1}'
        rendered = self.inline(text)
        self.headings.append(Heading(level, plain, rendered, hid))
        self.chunks.append((hid, []))
        return (
            f'<h{level} id="{hid}"><span>{rendered}</span>'
            f'<a class="anchor" href="#{hid}" aria-label="Link to this section">#</a></h{level}>'
        )

    def code_block(self, code: str, lang: str) -> str:
        body = highlight_dart(code) if lang == 'dart' else esc(code)
        return (
            '<div class="code"><button class="copy" type="button" aria-label="Copy code">'
            '<svg fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round" viewBox="0 0 24 24" width="16" height="16">'
            '<rect rx="2" ry="2" x="8" y="8" width="14" height="14"></rect>'
            '<path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path></svg></button>'
            f'<pre><code>{body}</code></pre></div>'
        )

    def table(self, head: list[str], rows: list[list[str]]) -> str:
        for row in rows:
            self._note(' '.join(row))
        thead = ''.join(f'<th>{self.inline(c)}</th>' for c in head)
        tbody = ''.join(
            '<tr>' + ''.join(f'<td>{self.inline(c)}</td>' for c in row) + '</tr>' for row in rows
        )
        return f'<table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>'


def parse_front_matter(source: str) -> tuple[dict[str, str], str]:
    if not source.startswith('---\n'):
        return {}, source
    end = source.index('\n---\n', 4)
    meta: dict[str, str] = {}
    for line in source[4:end].split('\n'):
        if not line.strip():
            continue
        key, _, value = line.partition(':')
        meta[key.strip()] = value.strip()
    return meta, source[end + 5:]
