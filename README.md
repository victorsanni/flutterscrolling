# Flutter Scrolling

Static study site for Flutter scrolling — guides, API recipes, and interactive examples — modelled on [renderobjects.com](https://renderobjects.com).

**Live site:** https://victorsanni.github.io/flutterscrolling/

## Structure

- `content/` — Markdown source for the 15 guides, 15 API pages, 3 examples, and 3 index pages.
- `build.py` + `sitegen/` — Zero-dependency Python static site generator, Dart syntax highlighter, and inline SVG diagram generator.
- `static/` — Stylesheet, client-side search (`⌘K` / `/`), self-hosted fonts, and interactive `<canvas>` demos.
- `example_code/` — Runnable Flutter package containing the exact Dart code and widget tests for the 3 examples.

## Build & Verify

```bash
# Build static HTML into ./site
python3 build.py

# Run example widget tests and static analysis
cd example_code
flutter pub get
flutter test
dart analyze --fatal-infos
```
