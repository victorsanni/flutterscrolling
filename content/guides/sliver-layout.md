---
title: Sliver Layout
nav: Sliver Layout
description: Why RenderSliver exists, how SliverConstraints go in, and how SliverGeometry comes back out.
card: BoxConstraints can't ask "what's visible at pixel 400?" Learn the SliverConstraints-in, SliverGeometry-out handshake.
---

This guide walks experienced Flutter developers through the sliver layout protocol (`RenderSliver`, `SliverConstraints`, and `SliverGeometry`). By the end, you'll understand why `BoxConstraints` cannot express lazy scrolling, what the viewport hands each sliver during layout, and how the three extents on `SliverGeometry` (`scrollExtent`, `paintExtent`, and `layoutExtent`) control everything on screen. We'll skip multi-child garbage collection and app-bar widgets for now — this is about the sliver layout handshake, and only that handshake.

## What This Guide Covers

- **Why `BoxConstraints` Aren't Enough** — What information a lazy list needs that `minWidth..maxHeight` cannot carry.
- **What `SliverConstraints` Tell a Sliver** — `scrollOffset`, `remainingPaintExtent`, `overlap`, and `crossAxisExtent`.
- **What `SliverGeometry` Answers Back** — Distinguishing `scrollExtent`, `paintExtent`, and `layoutExtent` with concrete numbers.
- **How `RenderViewport` Walks Slivers** — How one sliver's `SliverGeometry` shapes the next sliver's `SliverConstraints`.
- **Geometry Invariants** — The exact rules `SliverGeometry.debugAssertIsValid` enforces in debug mode.
- **Common Pitfalls** — Confusing `scrollOffset` with `pixels`, exceeding `remainingPaintExtent`, and forgetting `asBoxConstraints`.

## Why `BoxConstraints` Aren't Enough

A `RenderBox` receives four numbers (`minWidth`, `maxWidth`, `minHeight`, `maxHeight`) and returns a `Size(width, height)`. Nowhere in `BoxConstraints` can a parent say: *"The user has scrolled `420` pixels past your top edge, and only `300` pixels of screen height remain below you — only build and lay out the slice that shows."*

`RenderSliver` replaces `BoxConstraints` → `Size` with **`SliverConstraints` → `SliverGeometry`**. Instead of laying out a fixed rectangle, a sliver lays out *a slice of scrollable space*.

{{figure:sliver-protocol|RenderViewport passes SliverConstraints down to each RenderSliver, which assigns geometry before performLayout returns.}}

## What `SliverConstraints` Tell a Sliver

Inside `RenderSliver.performLayout()`, `this.constraints` gives you a `SliverConstraints` snapshot tailored to *this specific sliver's position* in the scroll view:

- **`scrollOffset`** (`>= 0.0`) — How many pixels of *this sliver* have already scrolled past the viewport's leading edge. While earlier slivers haven't finished scrolling off yet, your `scrollOffset` is `0.0`.
- **`remainingPaintExtent`** (`>= 0.0`) — How many pixels of visible viewport space remain from this sliver's layout start to the trailing edge of the viewport.
- **`overlap`** — How many pixels at the start of this sliver's space are currently painted over by an earlier pinned or floating sliver (such as `PinnedHeaderSliver`).
- **`crossAxisExtent`** — The width of a vertical viewport (or height of a horizontal one). Calling `constraints.asBoxConstraints()` turns this directly into tight cross-axis `BoxConstraints` for a child `RenderBox`.
- **`precedingScrollExtent`** — Total `scrollExtent` of all slivers before this one.

## What `SliverGeometry` Answers Back

A `RenderSliver` has no `size` getter. Instead, `performLayout` must assign `geometry = SliverGeometry(...)` before returning. Three fields do almost all the work:

1. **`scrollExtent`** — Total scrollable length this sliver contributes to `maxScrollExtent`, whether currently visible or not.
2. **`paintExtent`** — How many pixels this sliver actually paints inside the viewport right now (must never exceed `remainingPaintExtent`).
3. **`layoutExtent`** — How far `RenderViewport` should advance the starting position for the *next* sliver (defaults to `paintExtent` when omitted).

Walk through a concrete `200px` `SliverToBoxAdapter` inside a `500px` viewport as the user scrolls:

- **At `scrollOffset == 0.0`:** All `200px` are on screen. `scrollExtent: 200`, `paintExtent: 200`, `layoutExtent: 200`. The next sliver starts at `y = 200`.
- **At `scrollOffset == 80.0`:** Top `80px` have scrolled off; `120px` remain visible. `scrollExtent: 200`, `paintExtent: 120`, `layoutExtent: 120`. The next sliver starts at `y = 120`.
- **At `scrollOffset == 250.0`:** All `200px` have scrolled past the top. `scrollExtent: 200`, `paintExtent: 0`, `layoutExtent: 0` (`SliverGeometry.zero` except `scrollExtent: 200`). The next sliver starts at `y = 0` with `scrollOffset = 250 - 200 = 50.0`!

```dart
// Minimal ordinary scrolling box sliver (essence of RenderSliverToBoxAdapter):
@override
void performLayout() {
  if (child == null) {
    geometry = SliverGeometry.zero;
    return;
  }
  child!.layout(constraints.asBoxConstraints(), parentUsesSize: true);
  final double childExtent = child!.size.height; // assuming Axis.vertical
  final double painted = calculatePaintOffset(constraints, from: 0.0, to: childExtent);
  final double cache = calculateCacheOffset(constraints, from: 0.0, to: childExtent);

  geometry = SliverGeometry(
    scrollExtent: childExtent,
    paintExtent: painted,
    cacheExtent: cache,
    maxPaintExtent: childExtent,
    hitTestExtent: painted,
    hasVisualOverflow: childExtent > constraints.remainingPaintExtent || constraints.scrollOffset > 0.0,
  );
}
```

`RenderSliver` provides `calculatePaintOffset` and `calculateCacheOffset` as built-in helper methods so you don't have to hand-roll the clamping arithmetic between `[from, to]` and `[scrollOffset, scrollOffset + remainingPaintExtent]`.

## How `RenderViewport` Walks Slivers

Seeing how `RenderViewport` updates its running totals after each child makes every field obvious:

1. Before laying out sliver $i$, the viewport computes `sliverScrollOffset = max(0.0, totalScrollOffset - precedingScrollExtent)`.
2. Sliver $i$ runs `performLayout()` and writes `geometry`.
3. The viewport adds `geometry.scrollExtent` to `precedingScrollExtent`.
4. The viewport advances the paint cursor by `geometry.layoutExtent` and subtracts `geometry.layoutExtent` from `remainingPaintExtent` for sliver $i + 1$.
5. If `geometry.paintExtent > geometry.layoutExtent` (as in a [Sticky Header](/examples/sticky-header)), the extra painted height becomes `overlap` for sliver $i + 1$.

## Geometry Invariants

In debug mode, `SliverGeometry` asserts a handful of strict inequalities. Violating any of them throws a detailed `FlutterError` during layout:

- **`paintExtent <= remainingPaintExtent`** (specifically `paintOrigin + paintExtent <= remainingPaintExtent`) — A sliver may never claim to paint past the end of the viewport.
- **`layoutExtent <= paintExtent`** — You cannot push the next sliver further down than the space you actually paint.
- **`maxPaintExtent >= paintExtent`** — Your maximum possible paint size must be at least what you are painting right now.

## Common Pitfalls

**Treating `constraints.scrollOffset` as `ScrollPosition.pixels`.** They are equal *only* for the very first sliver in the viewport. If `300px` of slivers precede your sliver and `pixels == 320.0`, your `constraints.scrollOffset` is `20.0`, not `320.0`. If you truly need the global scroll offset, add `constraints.precedingScrollExtent + constraints.scrollOffset` (keeping in mind `scrollOffset` is clamped at `0.0` until scroll reaches your sliver).

**Forgetting floating-point epsilon when clamping `paintExtent`.** Subtraction like `childExtent - constraints.scrollOffset` can occasionally exceed `constraints.remainingPaintExtent` by `1e-13`, tripping debug assertions. Always clamp against `constraints.remainingPaintExtent` (or use `calculatePaintOffset`, which clamps for you).

That's the sliver layout protocol end to end: `SliverConstraints` tell each sliver how far past its start the user has scrolled and how much screen remains, and `SliverGeometry` reports total `scrollExtent`, visible `paintExtent`, and advancing `layoutExtent`. Next, we'll see how `SliverList` and `SliverGrid` use this protocol to build and garbage-collect thousands of box children lazily.
