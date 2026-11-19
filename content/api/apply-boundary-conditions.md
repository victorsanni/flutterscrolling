---
title: applyBoundaryConditions()
nav: applyBoundaryConditions()
description: Implement applyBoundaryConditions() in a custom ScrollPhysics to clamp or allow overscroll at edges.
---

The `applyBoundaryConditions(ScrollMetrics position, double value)` method inspects a proposed new `pixels` offset (`value`) and returns the **overscroll** — the portion of `value - position.pixels` that is refused.

- `ScrollPosition.setPixels` computes `actualPixels = value - overscroll`.
- Returning `0.0` accepts the entire move; any non-zero return must have the same sign as `value - position.pixels` and magnitude at most `(value - position.pixels).abs()`.

## Default Implementation

Delegates to `parent` if present, or returns `0.0` (no boundaries enforced):

```dart
double applyBoundaryConditions(ScrollMetrics position, double value) {
  if (parent == null) {
    return 0.0;
  }
  return parent!.applyBoundaryConditions(position, value);
}
```

## Allow Free Overscroll (iOS Bounce Style)

Example where `pixels` is allowed to move freely past both `minScrollExtent` and `maxScrollExtent` so a spring simulation can pull it back later.

```dart
@override
double applyBoundaryConditions(ScrollMetrics position, double value) => 0.0;
```

## Hard Clamp at Top, Bounce at Bottom

Example that refuses any movement below `minScrollExtent` (`0.0`) at the top edge while delegating bottom-edge behavior to `BouncingScrollPhysics`.

```dart
@override
double applyBoundaryConditions(ScrollMetrics position, double value) {
  // Already at or past the top edge, moving further out:
  if (value < position.pixels && position.pixels <= position.minScrollExtent) {
    return value - position.pixels;
  }
  // Crossing minScrollExtent on this frame:
  if (value < position.minScrollExtent && position.minScrollExtent < position.pixels) {
    return value - position.minScrollExtent;
  }
  return super.applyBoundaryConditions(position, value);
}
```

## Cap Maximum Overscroll Distance

Example that allows bouncing past the edges, up to a hard `80.0`-pixel ceiling in either direction.

```dart
static const double _maxOverscroll = 80.0;

@override
double applyBoundaryConditions(ScrollMetrics position, double value) {
  final double minAllowed = position.minScrollExtent - _maxOverscroll;
  final double maxAllowed = position.maxScrollExtent + _maxOverscroll;

  if (value < position.pixels && position.pixels <= minAllowed) {
    return value - position.pixels;
  }
  if (value < minAllowed && minAllowed < position.pixels) {
    return value - minAllowed;
  }
  if (position.pixels < maxAllowed && maxAllowed < value) {
    return value - maxAllowed;
  }
  if (maxAllowed <= position.pixels && position.pixels < value) {
    return value - position.pixels;
  }
  return 0.0;
}
```
