---
title: Scroll Views
nav: Scroll Views
description: How ListView, GridView, CustomScrollView, PageView, and SingleChildScrollView map onto the exact same building blocks.
---

This guide walks experienced Flutter developers through Flutter's high-level scroll view widgets (`CustomScrollView`, `ListView`, `GridView`, `PageView`, and `SingleChildScrollView`). By the end, you'll see that `ListView` and `GridView` are thin 20-line presets over `CustomScrollView`, know how `padding` and `SliverSafeArea` actually inject slivers, and choose the right scroll view on the first try. We'll skip nested coordination and 2D grids until the next group — this is about standard scroll views, and only standard scroll views.

## What This Guide Covers

- **`ScrollView` Is Just a Factory for `Scrollable` + `Viewport`** — What `ScrollView.build` actually constructs.
- **`ListView` and `GridView` Are Single-Sliver `CustomScrollView`s** — What `buildSlivers` returns for each constructor.
- **How `padding` Works Inside `BoxScrollView`** — Why `ListView(padding: ...)` wraps its sliver in `SliverPadding` instead of `Padding`.
- **`SingleChildScrollView` vs `ListView`** — Choosing between box-based repaint scrolling and sliver virtualization.
- **Choosing the Right Widget** — A quick decision table for real screens.
- **Common Pitfalls** — Wrapping slivers in `Padding`, using `ListView(children: ...)` for large lists, and `PageView` off-screen building.

## `ScrollView` Is Just a Factory for `Scrollable` + `Viewport`

Open `packages/flutter/lib/src/widgets/scroll_view.dart` and you'll find a pleasant surprise: `ScrollView` is a `StatelessWidget`. It holds no state of its own. Its `build` method does three small things:

1. Resolves `PrimaryScrollController` if `controller == null` and the view is primary.
2. Calls `buildSlivers(context)` to get the `List<Widget>` of slivers.
3. Returns a `Scrollable` whose `viewportBuilder` builds either a `Viewport` (normal) or a `ShrinkWrappingViewport` (`shrinkWrap: true`).

`CustomScrollView` is the most direct subclass of `ScrollView` in the entire framework — its `buildSlivers` method literally returns `slivers`!

## `ListView` and `GridView` Are Single-Sliver `CustomScrollView`s

`ListView` and `GridView` both extend `BoxScrollView` (which extends `ScrollView`). Neither has a special viewport or special gesture handling. Each constructor simply picks one sliver inside `buildChildLayout`:

| High-level widget | Sliver returned by `buildChildLayout` |
| --- | --- |
| `ListView(...)` / `ListView.builder(...)` | `SliverList` (when no extent is given) |
| `ListView(..., itemExtent: h)` | `SliverFixedExtentList` |
| `ListView(..., prototypeItem: w)` | `SliverPrototypeExtentList` |
| `ListView(..., itemExtentBuilder: fn)` | `SliverVariedExtentList` |
| `ListView.separated(...)` | `SliverList` with `2 * n - 1` children interleaving items and separators |
| `GridView.count` / `.extent` / `.builder` | `SliverGrid` |

**Graduating from `ListView` to `CustomScrollView` changes zero scrolling behavior** — it just lets `buildSlivers` return two or more slivers (say, a `PinnedHeaderSliver`, a `SliverPadding` around a `SliverGrid`, and a `SliverList`) inside one shared `Viewport` and one shared `ScrollPosition`.

```dart
// Identical runtime tree to ListView.builder(padding: EdgeInsets.all(16), itemExtent: 56, ...):
CustomScrollView(
  slivers: <Widget>[
    SliverPadding(
      padding: const EdgeInsets.all(16.0),
      sliver: SliverFixedExtentList.builder(
        itemExtent: 56.0,
        itemCount: items.length,
        itemBuilder: itemBuilder,
      ),
    ),
  ],
)
```

## How `padding` Works Inside `BoxScrollView`

Notice `SliverPadding` in the snippet above. If you wrapped a `ListView` in a normal `Padding(padding: EdgeInsets.all(16))`, the viewport window itself would shrink by `16px` on every side, clipping scrolling items `16px` away from the screen edges instead of letting them scroll cleanly behind the top and bottom status/navigation bars!

`BoxScrollView` (`ListView` and `GridView`) handles `padding` properly:

- If you pass `padding:`, `BoxScrollView.buildSlivers` wraps the inner sliver in `SliverPadding(padding: padding!, sliver: sliver)`.
- If you leave `padding: null`, `BoxScrollView` checks `MediaQuery.maybePaddingOf(context)` along the scroll axis (for example, the iOS notch and home indicator) and automatically inserts a `SliverPadding` with those safe-area insets!

**When you switch from `ListView` to `CustomScrollView`, `BoxScrollView`'s automatic `MediaQuery` padding is no longer inserted for you.** Wrap slivers that need safe-area spacing in `SliverSafeArea` or `SliverPadding` explicitly.

## `SingleChildScrollView` vs `ListView`

`SingleChildScrollView` does *not* extend `ScrollView` and does *not* use slivers. It pairs `Scrollable` with `_SingleChildViewport` (a single-child `RenderBox` viewport just like [Minimal Viewport](/examples/minimal-viewport)).

Use `SingleChildScrollView` when:

- You have a bounded form, settings card, or dialog body with a handful of heterogeneous widgets that might overflow on a small phone or when the soft keyboard opens.
- You need `IntrinsicWidth` or `CrossAxisAlignment.stretch` across the whole column without sliver ceremony.

Use `ListView.builder` / `CustomScrollView` whenever child count scales with data or items contain images and heavy subtrees.

## Choosing the Right Widget

- **One short form that scrolls when the keyboard opens** → `SingleChildScrollView`
- **One uniform list of items** → `ListView.builder` (pass `itemExtent` or `prototypeItem` if heights match)
- **Header + grid + list scrolling together** → `CustomScrollView`
- **Full-viewport or fractional-viewport swipeable pages** → `PageView.builder` (uses `Viewport` + `SliverFillViewport` + `PageScrollPhysics` + `PageController`)

## Common Pitfalls

**Passing a normal `RenderBox` widget directly into `CustomScrollView.slivers`.** Every direct child of `CustomScrollView.slivers` must produce a `RenderSliver`. Passing a `Container` or `Padding` throws `"A RenderViewport expected a child of type RenderSliver but received a child of type RenderPadding"`. Use `SliverToBoxAdapter` for single boxes and `SliverPadding` for insets.

**Using the default `ListView(children: [...])` constructor with a `.map(...).toList()` over hundreds of items.** Even though `ListView(children: ...)` still mounts elements lazily via `SliverChildListDelegate`, Dart evaluates your `.map(...).toList()` eagerly on every parent rebuild, allocating all `Widget` instances up front. Use `ListView.builder` so only visible indices allocate widgets.

That wraps up the `Slivers` group! You now know the whole core scrolling stack from `Scrollable` down to `SliverList` and `CustomScrollView`. The final three guides in **Going Further** tackle specialized topics you can read whenever you hit them: programmatic reveal (`ensureVisible`), `NestedScrollView`, and 2D scrolling.
