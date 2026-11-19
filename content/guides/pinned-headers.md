---
title: Pinned and Floating Headers
nav: Pinned Headers
description: Choosing between PinnedHeaderSliver, SliverResizingHeader, SliverFloatingHeader, SliverPersistentHeader, and SliverAppBar.
---

This guide walks experienced Flutter developers through Flutter's header slivers. By the end, you'll know which of the four focused header slivers (`PinnedHeaderSliver`, `SliverResizingHeader`, `SliverFloatingHeader`, and `SliverPersistentHeader`) fits each UI pattern, and how all of them work under the hood using `layoutExtent`, `paintExtent`, and `overlap`. We'll skip `NestedScrollView` overlap injection for now — this is about single-viewport headers, and only single-viewport headers.

## What This Guide Covers

- **One Trick Behind Every Sticky Header** — How shrinking `layoutExtent` while keeping `paintExtent` lets content slide underneath.
- **The Three Simple Header Widgets** — `PinnedHeaderSliver`, `SliverResizingHeader`, and `SliverFloatingHeader` (and why Flutter added them).
- **`SliverPersistentHeader` and `SliverAppBar`** — When you need `shrinkOffset`-driven custom builds or full Material app bar chrome.
- **Stacking Multiple Headers with `overlap`** — What happens when two pinned slivers meet at the top edge.
- **Common Pitfalls** — Forgetting `shouldRebuild` on a delegate, hardcoding heights that clip large fonts, and obstructing `ensureVisible`.

## One Trick Behind Every Sticky Header

Every pinned or floating header in Flutter relies on one distinction in `SliverGeometry`:

- `paintExtent` is how tall the header **draws** on screen.
- `layoutExtent` is how far down the header **pushes the next sliver**.

While a `56px` header is still scrolling toward the top edge (`constraints.scrollOffset == 0`), both `paintExtent` and `layoutExtent` are `56.0`. Once earlier slivers scroll away and `constraints.scrollOffset` climbs from `0` to `56`, `paintExtent` stays `56.0` while `layoutExtent` shrinks from `56.0` down to `0.0`. The sliver right after the header now lays out starting at `y = 0` — sliding underneath the header — while the header continues painting on top of it.

You can read and interact with every line of that calculation in the [Sticky Header Sliver](/examples/sticky-header) example.

## The Three Simple Header Widgets

For years, pinning any widget inside a `CustomScrollView` forced you to write a verbose `SliverPersistentHeaderDelegate` subclass with hardcoded `minExtent` and `maxExtent` numbers. Modern Flutter ships three composable widgets that measure their child automatically without a delegate class:

1. **`PinnedHeaderSliver`** — Takes any single `child` widget, measures its natural box height during layout, scrolls normally until reaching the viewport's leading edge, and pins there permanently.
2. **`SliverResizingHeader`** — Smoothly shrinks a `child` between the natural height of a `maxExtentPrototype` widget and a `minExtentPrototype` widget as the user scrolls, then stays pinned at `minExtentPrototype`'s height.
3. **`SliverFloatingHeader`** — Scrolls off-screen as the user scrolls down, and immediately slides back into view at the top of the viewport as soon as the user reverses direction (`userScrollDirection == ScrollDirection.forward`), snapping cleanly to fully shown or fully hidden when scrolling stops.

```dart
CustomScrollView(
  slivers: <Widget>[
    const PinnedHeaderSliver(
      child: ColoredBox(
        color: Color(0xFF111111),
        child: Padding(
          padding: EdgeInsets.all(16.0),
          child: Text('Pinned search bar — sizes itself automatically'),
        ),
      ),
    ),
    SliverList.builder(
      itemCount: 50,
      itemBuilder: (BuildContext context, int i) => ListTile(title: Text('Item $i')),
    ),
  ],
)
```

**Reach for `PinnedHeaderSliver`, `SliverResizingHeader`, or `SliverFloatingHeader` first.** Because they measure child widgets directly during layout instead of asking you for hardcoded `double` extents, they adapt automatically when users enable large accessibility text scales.

## `SliverPersistentHeader` and `SliverAppBar`

You still want `SliverPersistentHeader` (or Material's `SliverAppBar`, which wraps `SliverPersistentHeader` internally) in two situations:

- Your header needs the exact pixel `shrinkOffset` and `overlapsContent` boolean during `build` to cross-fade titles, scale avatars, or toggle elevation shadows.
- You want `SliverAppBar`'s built-in combinations of `pinned`, `floating`, `snap`, `stretch` (overscroll zoom), and `FlexibleSpaceBar`.

```dart
class SectionHeaderDelegate extends SliverPersistentHeaderDelegate {
  const SectionHeaderDelegate({required this.title});
  final String title;

  @override
  double get minExtent => 48.0;

  @override
  double get maxExtent => 96.0;

  @override
  Widget build(BuildContext context, double shrinkOffset, bool overlapsContent) {
    final double t = (shrinkOffset / (maxExtent - minExtent)).clamp(0.0, 1.0);
    return ColoredBox(
      color: overlapsContent ? const Color(0xFF1A1A1A) : const Color(0xFF111111),
      child: Align(
        alignment: Alignment.lerp(Alignment.bottomLeft, Alignment.centerLeft, t)!,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0),
          child: Text(title),
        ),
      ),
    );
  }

  @override
  bool shouldRebuild(SectionHeaderDelegate oldDelegate) => title != oldDelegate.title;
}
```

## Stacking Multiple Headers with `overlap`

What happens if you place *two* `PinnedHeaderSliver`s inside the same `CustomScrollView`?

When the first `56px` header is pinned, its `paintExtent` (`56.0`) exceeds its `layoutExtent` (`0.0`) by `56.0`. `RenderViewport` passes that `56.0` difference into the next sliver as `constraints.overlap`.

`PinnedHeaderSliver` sets `paintOrigin: constraints.overlap`. As a result, the second `PinnedHeaderSliver` pins at `y = 56.0` right *below* the first header rather than painting directly over it! (If instead you want section headers that *push* the previous section's header off-screen, packages like `sliver_tools` or a custom multi-sliver coordinate their `paintOrigin`s accordingly.)

## Common Pitfalls

**Returning `false` from `SliverPersistentHeaderDelegate.shouldRebuild` when fields changed.** If `shouldRebuild` always returns `false`, rebuilding the parent widget with a new `title` or theme color leaves the header showing stale UI until `shrinkOffset` happens to change. Compare every field your `build`, `minExtent`, or `maxExtent` reads.

**Hardcoding `minExtent` / `maxExtent` smaller than the child's text height.** In `SliverPersistentHeaderDelegate`, your `build` output is forced into tight height constraints between `minExtent` and `maxExtent`. Under `200%` system text scaling, a hardcoded `48.0` header with two lines of text will overflow vertically; prefer `PinnedHeaderSliver` or include `MediaQuery.textScalerOf(context)` in your extent math.

**Using `snap: true` without `floating: true` on `SliverAppBar`.** `SliverAppBar` asserts that `snap` requires `floating: true` (and a `vsync` ticker), because snapping animates the floating header open or closed when the user lifts their finger mid-reveal.

That's pinned, resizing, and floating headers end to end: one `layoutExtent` vs `paintExtent` split, wrapped in three zero-boilerplate widgets for everyday layouts and `SliverPersistentHeader` / `SliverAppBar` when you need `shrinkOffset`-driven transitions. Next, we'll step back and see how `ListView`, `GridView`, `CustomScrollView`, and `SingleChildScrollView` assemble everything we've covered so far.
