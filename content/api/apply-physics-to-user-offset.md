---
title: applyPhysicsToUserOffset()
nav: applyPhysicsToUserOffset()
description: Implement applyPhysicsToUserOffset() in a custom ScrollPhysics to scale or resist finger drags.
---

The `applyPhysicsToUserOffset(ScrollMetrics position, double offset)` method converts a raw pointer drag delta (`offset`, in logical pixels along the scroll axis) into the delta that `ScrollPosition` will subtract from `pixels`.

- A positive `offset` means dragging forward (down/right, decreasing `pixels`).
- A negative `offset` means dragging in reverse (up/left, increasing `pixels`).

## Default Implementation

Delegates to `parent` if present, or returns `offset` unchanged (`1:1` finger tracking):

```dart
double applyPhysicsToUserOffset(ScrollMetrics position, double offset) {
  if (parent == null) {
    return offset;
  }
  return parent!.applyPhysicsToUserOffset(position, offset);
}
```

## Constant Damping - Heavy Scroll Feel

Example that halves user drag speed everywhere while preserving any overscroll friction applied by `parent`.

```dart
@override
double applyPhysicsToUserOffset(ScrollMetrics position, double offset) {
  return super.applyPhysicsToUserOffset(position, offset * 0.5);
}
```

## Rubber-Band Resistance When Overscrolled

Example that tracks `1:1` inside `[minScrollExtent, maxScrollExtent]` and progressively stiffens the drag once the user pulls past either edge.

```dart
@override
double applyPhysicsToUserOffset(ScrollMetrics position, double offset) {
  if (!position.outOfRange) {
    return super.applyPhysicsToUserOffset(position, offset);
  }
  final double overscroll = position.pixels < position.minScrollExtent
      ? position.minScrollExtent - position.pixels
      : position.pixels - position.maxScrollExtent;
  final double ratio = (1.0 - overscroll / position.viewportDimension).clamp(0.15, 1.0);
  return offset * ratio;
}
```

## One-Way Ratchet - Block Dragging Backward

Example where the user may drag down the list (`offset < 0`, increasing `pixels`) freely, while dragging back toward the top (`offset > 0`) is ignored.

```dart
@override
double applyPhysicsToUserOffset(ScrollMetrics position, double offset) {
  if (offset > 0.0) {
    return 0.0;
  }
  return super.applyPhysicsToUserOffset(position, offset);
}
```
