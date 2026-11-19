---
title: Scroll Physics
nav: Scroll Physics
description: How immutable physics chains control drag resistance, edge boundaries, and liftoff simulations.
---

This guide walks experienced Flutter developers through `ScrollPhysics`. By the end, you'll understand how physics instances chain together through `applyTo`, what each of the four core physics methods decides, and how Flutter's built-in physics classes differ. We'll skip `AnimationController` internals and sliver layout — this is about the rules of motion, and only the rules of motion.

## What This Guide Covers

- **An Immutable Chain of Rules** — Why `ScrollPhysics` holds no mutable state and delegates unsolved work to `parent`.
- **How `applyTo` Builds the Chain** — Why forgetting `applyTo` silently erases your custom physics subclass.
- **The Four Decisions Physics Makes** — Drag resistance, boundary enforcement, ballistic simulations, and resize adjustments.
- **Built-in `ScrollPhysics` Classes** — What `ClampingScrollPhysics`, `BouncingScrollPhysics`, `NeverScrollableScrollPhysics`, `AlwaysScrollableScrollPhysics`, and `PageScrollPhysics` actually override.
- **Common Pitfalls** — Missing `applyTo`, misunderstanding `applyBoundaryConditions` return values, and breaking overscroll springs.

## An Immutable Chain of Rules

`ScrollPhysics` is a `const`-constructible strategy object with a single field, `final ScrollPhysics? parent`, and zero mutable state.

Because physics objects hold no state of their own, every method receives a read-only `ScrollMetrics` snapshot (`pixels`, `minScrollExtent`, `maxScrollExtent`, `viewportDimension`) and returns a number or a `Simulation`. Each link in the chain overrides only the decisions it cares about and delegates the rest to `super`, which forwards to `parent`.

{{figure:physics-chain|A custom SnapScrollPhysics wrapped around the platform's BouncingScrollPhysics and RangeMaintainingScrollPhysics.}}

## How `applyTo` Builds the Chain

When you write `ListView(physics: const SnapScrollPhysics(itemExtent: 220))`, `ScrollableState` combines your widget's physics with the ambient `ScrollBehavior` physics:

```dart
// Inside ScrollableState._updatePosition:
_physics = widget.physics != null
    ? widget.physics!.applyTo(ambientPhysics)
    : ambientPhysics;
```

Look closely at `widget.physics!.applyTo(ambientPhysics)`. Your widget's physics sits at the **front** of the chain so its overrides run first, and `ambientPhysics` (for example `BouncingScrollPhysics(parent: RangeMaintainingScrollPhysics())`) becomes its `parent` fallback.

Every `ScrollPhysics` subclass **must** override `applyTo` using `buildParent(ancestor)`:

```dart
class SlowDragPhysics extends ScrollPhysics {
  const SlowDragPhysics({super.parent});

  @override
  SlowDragPhysics applyTo(ScrollPhysics? ancestor) {
    return SlowDragPhysics(parent: buildParent(ancestor));
  }

  @override
  double applyPhysicsToUserOffset(ScrollMetrics position, double offset) {
    return super.applyPhysicsToUserOffset(position, offset * 0.5);
  }
}
```

**Forgetting to override `applyTo` is the single most common `ScrollPhysics` bug.** The base implementation on `ScrollPhysics` returns a plain `ScrollPhysics(parent: buildParent(ancestor))`, which strips your subclass off the chain before a single pixel ever moves.

## The Four Decisions Physics Makes

Nearly all custom scroll physics come down to four methods:

1. `applyPhysicsToUserOffset(ScrollMetrics position, double offset)` transforms a raw finger drag `offset` before it is subtracted from `pixels`. Returning `offset` gives `1:1` tracking; `BouncingScrollPhysics` applies progressive friction here when `position.outOfRange` is true so pulling past the top feels rubbery.
2. `applyBoundaryConditions(ScrollMetrics position, double value)` inspects a proposed new `pixels` (`value`) and returns **how many pixels of movement are refused** (the overscroll). Returning `0.0` accepts the entire move; returning `value - position.pixels` refuses all of it.
3. `createBallisticSimulation(ScrollMetrics position, double velocity)` runs when the finger lifts (or bounds change) and returns a `Simulation?` describing `pixels` over time. Returning `null` puts the position straight to idle.
4. `adjustPositionForNewDimensions(...)` decides what `pixels` should be when `minScrollExtent`, `maxScrollExtent`, or `viewportDimension` changes during layout.

```dart
// Clamping at the top edge inside applyBoundaryConditions:
if (value < position.pixels && position.pixels <= position.minScrollExtent) {
  // Already at or past the top, and trying to go further: refuse the whole move.
  return value - position.pixels;
}
if (value < position.minScrollExtent && position.minScrollExtent < position.pixels) {
  // Crossing the top edge this frame: refuse only the part past minScrollExtent.
  return value - position.minScrollExtent;
}
```

**The value returned by `applyBoundaryConditions` is subtracted from `value` by `setPixels` (`actualNewPixels = value - overscroll`) and reported in `OverscrollNotification`.** If your math returns a value larger than the frame's delta `(value - position.pixels)` in magnitude, Flutter throws a debug assertion immediately.

## Built-in `ScrollPhysics` Classes

Understanding the five standard subclasses saves you from writing custom physics when a composition of built-ins already does the job:

- **`ClampingScrollPhysics`** (Android / Linux / Windows default) — Refuses movement past `minScrollExtent` and `maxScrollExtent` in `applyBoundaryConditions` (feeding Android's stretch/glow indicator via the returned overscroll) and uses `ClampingScrollSimulation` for friction flings.
- **`BouncingScrollPhysics`** (iOS / macOS default) — Returns `0.0` from `applyBoundaryConditions` so `pixels` can move past the edges, attenuates user drag while overscrolled in `applyPhysicsToUserOffset`, and uses `BouncingScrollSimulation` to spring back into range.
- **`AlwaysScrollableScrollPhysics`** — Overrides `shouldAcceptUserOffset` to return `true` even when `minScrollExtent == maxScrollExtent` (for example, a short list that still needs pull-to-refresh).
- **`NeverScrollableScrollPhysics`** — Overrides `allowUserScrolling` and `allowImplicitScrolling` to return `false`, disabling touch drags and accessibility scroll actions while leaving programmatic `jumpTo` and `animateTo` working.
- **`RangeMaintainingScrollPhysics`** — Placed at the tail of every default chain by `ScrollBehavior`; keeps `pixels` clamped if content shrinks while the user is not overscrolling.

Because chains compose with `applyTo` or `parent:`, you can combine them directly:

```dart
// Bounces even when there are only two items in the list (required for RefreshIndicator on iOS):
physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
```

## Common Pitfalls

**Forgetting `shouldUpdate` when your physics has fields.** If your `ScrollPhysics` subclass stores parameters (like `itemExtent` in [Snapping Physics](/examples/snapping-physics)), override `shouldUpdate(covariant MyPhysics old)` to compare those fields. By default `ScrollPhysics` only checks `runtimeType` up the parent chain, so changing `itemExtent` on rebuild would be ignored.

**Returning a simulation when already at the target.** In `createBallisticSimulation`, always check whether `(target - position.pixels).abs() < tolerance.distance` (or `target == position.pixels`) and return `null`. Returning a `ScrollSpringSimulation` whose start and end are identical wastes an animation frame before settling.

**Overriding `createBallisticSimulation` without delegating out-of-range overscroll.** When `position.outOfRange` is true and velocity points away from the list, delegate to `super.createBallisticSimulation(position, velocity)` unless you specifically intend to replace the platform's edge return spring.

That's `ScrollPhysics` end to end: an immutable parent chain built via `applyTo` that shapes user deltas, guards boundaries, and creates liftoff simulations. Next, we'll look at `ScrollActivity` — the stateful driver that actually runs drags, flings, and `animateTo` curves over time.
