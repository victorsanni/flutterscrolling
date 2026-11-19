"""A compact Dart syntax highlighter that emits <span class="t-*"> tokens.

It is a tokenizer, not a parser: good enough for documentation snippets, and
it never changes the text (highlight_dart(x) with tags stripped == escape(x)).
"""

from __future__ import annotations

import html
import re

KEYWORDS = {
    'abstract', 'as', 'async', 'await', 'base', 'class', 'const', 'covariant',
    'deferred', 'dynamic', 'enum', 'export', 'extends', 'extension', 'external',
    'factory', 'false', 'final', 'get', 'hide', 'implements', 'import',
    'interface', 'is', 'late', 'library', 'mixin', 'new', 'null', 'on',
    'operator', 'part', 'required', 'sealed', 'set', 'show', 'static', 'super',
    'this', 'true', 'typedef', 'var', 'void', 'with',
}
CONTROL = {
    'assert', 'break', 'case', 'catch', 'continue', 'default', 'do', 'else',
    'finally', 'for', 'if', 'in', 'rethrow', 'return', 'switch', 'throw',
    'try', 'while', 'yield',
}
BUILTIN_TYPES = {'int', 'double', 'bool', 'num', 'Never'}

TOKEN = re.compile(
    r'''
    (?P<comment>//[^\n]*|/\*.*?\*/)
  | (?P<string>r?\'\'\'.*?\'\'\'|r?""".*?"""|r?'(?:\\.|[^'\\\n])*'|r?"(?:\\.|[^"\\\n])*")
  | (?P<annotation>@[A-Za-z_]\w*)
  | (?P<number>\b(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b)
  | (?P<ident>[A-Za-z_$][A-Za-z0-9_$]*)
  | (?P<open>[(\[{])
  | (?P<close>[)\]}])
  | (?P<punct>[;,.:?!=<>+\-*/%&|^~]+)
    ''',
    re.S | re.X,
)

BRACKET_COLORS = 6


def _span(cls: str, text: str) -> str:
    return f'<span class="t-{cls}">{html.escape(text, quote=False)}</span>'


def highlight_dart(code: str) -> str:
    out: list[str] = []
    depth = 0
    pos = 0
    for match in TOKEN.finditer(code):
        if match.start() > pos:
            out.append(html.escape(code[pos:match.start()], quote=False))
        pos = match.end()
        kind = match.lastgroup
        text = match.group()
        if kind == 'comment':
            out.append(_span('c', text))
        elif kind == 'string':
            out.append(_span('s', text))
        elif kind == 'annotation':
            out.append(_span('k', text))
        elif kind == 'number':
            out.append(_span('n', text))
        elif kind == 'ident':
            bare = text.lstrip('_')
            if text in KEYWORDS:
                out.append(_span('k', text))
            elif text in CONTROL:
                out.append(_span('f', text))
            elif text in BUILTIN_TYPES or (bare[:1].isupper()):
                out.append(_span('t', text))
            elif code[pos:pos + 1] == '(':
                out.append(_span('m', text))
            else:
                out.append(html.escape(text, quote=False))
        elif kind == 'open':
            out.append(_span(f'b{depth % BRACKET_COLORS}', text))
            depth += 1
        elif kind == 'close':
            depth = max(0, depth - 1)
            out.append(_span(f'b{depth % BRACKET_COLORS}', text))
        else:
            out.append(_span('p', text))
    if pos < len(code):
        out.append(html.escape(code[pos:], quote=False))
    return ''.join(out)
