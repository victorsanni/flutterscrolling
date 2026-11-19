---
title: createBallisticSimulation()
nav: createBallisticSimulation()
description: Implement createBallisticSimulation() in a custom ScrollPhysics to drive flings, springs, and snapping after liftoff.
---

The `createBallisticSimulation(ScrollMetrics position, double velocity)` method returns the `Simulation` that drives `pixels` over time once the user lifts their finger (or after content bounds change).

- Return `null` when the position is already at rest where it belongs (`IdleScrollActivity`).
- Return a `Simulation` (`ScrollSpringSimulation`, `ClampingScrollSimulation`, `FrictionSimulation`, etc.) to start a `BallisticScrollActivity`.

## Default Implementation

Delegates to `parent` if present, or returns `null`:

```dart
Simulation? createBallisticSimulation(ScrollMetrics position, double velocity) {
  if (parent == null) {
    return null;
  }
  return parent!.createBallisticSimulation(position, velocity);
}
```

## Disable Coasting - Stop Dead on Finger Up

Example where lifting the finger stops scrolling immediately inside bounds, while still springing back if overscrolled past an edge.

```dart
@override
Simulation? createBallisticSimulation(ScrollMetrics position, double velocity) {
  if (position.outOfRange) {
    return super.createBallisticSimulation(position, velocity);
  }
  return null;
}
```

## Snap to Fixed Intervals (`ScrollSpringSimulation`)

Example that lands on the nearest multiple of `snapExtent`, advancing by one step when `velocity` exceeds `tolerance.velocity`.

```dart
@override
Simulation? createBallisticSimulation(ScrollMetrics position, double velocity) {
  if ((velocity <= 0.0 && position.pixels <= position.minScrollExtent) ||
      (velocity >= 0.0 && position.pixels >= position.maxScrollExtent)) {
    return super.createBallisticSimulation(position, velocity);
  }
  final Tolerance tolerance = toleranceFor(position);
  double step = position.pixels / snapExtent;
  if (velocity < -tolerance.velocity) {
    step -= 0.5;
  } else if (velocity > tolerance.velocity) {
    step += 0.5;
  }
  final double target = (step.roundToDouble() * snapExtent).clamp(
    position.minScrollExtent,
    position.maxScrollExtent,
  );
  if (target == position.pixels) {
    return null;
  }
  return ScrollSpringSimulation(
    spring,
    position.pixels,
    target,
    velocity,
    tolerance: tolerance,
  );
}
```

## Custom Friction Drag (`FrictionSimulation`)

Example that replaces platform deceleration with a custom drag coefficient (`0.05` coasts further; `0.3` stops quickly) inside bounds.

```dart
@override
Simulation? createBallisticSimulation(ScrollMetrics position, double velocity) {
  final Tolerance tolerance = toleranceFor(position);
  if (position.outOfRange) {
    return super.createBallisticSimulation(position, velocity);
  }
  if (velocity.abs() < tolerance.velocity) {
    return null;
  }
  return FrictionSimulation(
    0.05, // drag coefficient (0 < drag < 1)
    position.pixels,
    velocity,
    tolerance: tolerance,
  );
}
```
