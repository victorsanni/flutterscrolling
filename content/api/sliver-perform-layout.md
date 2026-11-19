---
title: performLayout()
nav: performLayout()
description: Implement performLayout() in a custom RenderSliver or RenderSliverSingleBoxAdapter.
---

`RenderSliver.performLayout()` has two responsibilities:

- Lay out any visible children using `this.constraints` (`SliverConstraints`).
- Assign a valid `SliverGeometry` to `this.geometry` before returning.

## Default Implementation - There Is None

`RenderSliver` does not provide a default `performLayout()`. Every concrete sliver subclass must set `geometry` on every call — leaving `geometry` null triggers a framework assertion immediately after `performLayout()` returns.

## Childless Spacer Sliver

Example of a sliver with no child that contributes a fixed `extent` of scrollable blank space (similar to `SliverToBoxAdapter(child: SizedBox(height: extent))` without allocating a `RenderBox`).

```dart
class RenderSliverGap extends RenderSliver {
  RenderSliverGap(this.extent);
  double extent;

  @override
  void performLayout() {
    final double painted = calculatePaintOffset(constraints, from: 0.0, to: extent);
    final double cache = calculateCacheOffset(constraints, from: 0.0, to: extent);
    geometry = SliverGeometry(
      scrollExtent: extent,
      paintExtent: painted,
      cacheExtent: cache,
      maxPaintExtent: extent,
    );
  }
}
```

## Single Child - Fill Remaining Viewport Space

Example where a single `RenderBox` stretches to fill whatever space remains in the viewport when content above it is short, while never shrinking smaller than its own intrinsic height (the core idea of `SliverFillRemaining(hasScrollBody: false)`).

```dart
@override
void performLayout() {
  if (child == null) {
    geometry = SliverGeometry.zero;
    return;
  }
  // Measure child's natural height first:
  child!.layout(constraints.asBoxConstraints(), parentUsesSize: true);
  final double naturalExtent = switch (constraints.axis) {
    Axis.vertical => child!.size.height,
    Axis.horizontal => child!.size.width,
  };
  final double extent = math.max(
    naturalExtent,
    constraints.viewportMainAxisExtent - constraints.precedingScrollExtent,
  );
  if (extent != naturalExtent) {
    child!.layout(
      constraints.asBoxConstraints(minExtent: extent, maxExtent: extent),
      parentUsesSize: true,
    );
  }
  final double painted = calculatePaintOffset(constraints, from: 0.0, to: extent);
  geometry = SliverGeometry(
    scrollExtent: extent,
    paintExtent: painted,
    maxPaintExtent: extent,
    hasVisualOverflow: extent > constraints.remainingPaintExtent || constraints.scrollOffset > 0.0,
  );
  setChildParentData(child!, constraints, geometry!);
}
```

## Single Child - Parallax / Overscroll Stretch Header

Example where pulling past the top of a `BouncingScrollPhysics` viewport (`constraints.overlap < 0.0` or `precedingScrollExtent == 0.0`) stretches the header box to cover the gap.

```dart
@override
void performLayout() {
  if (child == null) {
    geometry = SliverGeometry.zero;
    return;
  }
  final double over = constraints.overlap < 0.0 ? -constraints.overlap : 0.0;
  child!.layout(
    constraints.asBoxConstraints(
      minExtent: baseHeight + over,
      maxExtent: baseHeight + over,
    ),
    parentUsesSize: true,
  );
  final double painted = math.min(
    math.max(0.0, baseHeight - constraints.scrollOffset) + over,
    constraints.remainingPaintExtent,
  );
  geometry = SliverGeometry(
    scrollExtent: baseHeight,
    paintOrigin: -over,
    paintExtent: painted,
    layoutExtent: math.min(painted - over, math.max(0.0, painted)),
    maxPaintExtent: baseHeight + over,
  );
}
```
