---
title: SliverGeometry
nav: SliverGeometry
description: Construct a valid SliverGeometry inside RenderSliver.performLayout().
---

`SliverGeometry` is the immutable answer a `RenderSliver` writes to `this.geometry` before `performLayout()` returns.

Every debug build validates `geometry` with `debugAssertIsValid`, enforcing `layoutExtent <= paintExtent`, `paintExtent <= maxPaintExtent`, and `paintOrigin + paintExtent <= constraints.remainingPaintExtent`.

## Constructor Fields and Defaults

| Field | Default | Meaning |
| --- | --- | --- |
| `scrollExtent` | `0.0` | Total scrollable length contributed to `maxScrollExtent` |
| `paintExtent` | `0.0` | Pixels painted inside the viewport right now |
| `paintOrigin` | `0.0` | Offset from this sliver's layout start where painting begins |
| `layoutExtent` | `paintExtent` | How far the viewport advances the *next* sliver's start |
| `maxPaintExtent` | `0.0` | Largest extent this sliver could ever paint (`>= paintExtent`) |
| `maxScrollObstructionExtent` | `0.0` | Pixels permanently obstructing content for `ensureVisible` |
| `hitTestExtent` | `paintExtent` | Main-axis range accepting pointer hits |
| `visible` | `paintExtent > 0.0` | Whether `RenderViewport` calls `paint()` on this sliver |
| `hasVisualOverflow` | `false` | Hint that children extend outside `paintExtent` and may need clipping |
| `scrollOffsetCorrection` | `null` | Non-zero value aborts layout, adjusts `offset` by this delta, and retries |
| `cacheExtent` | *(calculated)* | Portion of `remainingCacheExtent` consumed by this sliver |

## Empty / Collapsed Sliver (`SliverGeometry.zero`)

Example when a sliver has no child or `0.0` extent.

```dart
if (child == null) {
  geometry = SliverGeometry.zero;
  return;
}
```

## Ordinary Scrolling Sliver

Example where `layoutExtent` equals `paintExtent`, so the next sliver starts immediately after the visible portion of this sliver.

```dart
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
```

## Pinned Sliver (`layoutExtent < paintExtent`)

Example where `paintExtent` stays full height while `layoutExtent` shrinks to `0.0`, allowing subsequent slivers to slide underneath.

```dart
final double layoutExtent = clampDouble(
  childExtent - constraints.scrollOffset,
  0.0,
  constraints.remainingPaintExtent,
);
final double paintExtent = math.min(
  childExtent,
  constraints.remainingPaintExtent - constraints.overlap,
);

geometry = SliverGeometry(
  scrollExtent: childExtent,
  paintOrigin: constraints.overlap,
  paintExtent: paintExtent,
  layoutExtent: layoutExtent,
  maxPaintExtent: childExtent,
  maxScrollObstructionExtent: childExtent,
  hasVisualOverflow: true,
);
```

## Request a Scroll Offset Correction Mid-Layout

Example when a lazy sliver discovers an item above the viewport was taller than previously estimated. When `scrollOffsetCorrection` is non-null, `RenderViewport` immediately adjusts `ViewportOffset` and re-runs layout; no other fields on `SliverGeometry` need to be populated.

```dart
if (drift != 0.0) {
  geometry = SliverGeometry(scrollOffsetCorrection: drift);
  return;
}
```
