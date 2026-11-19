---
title: Snapping Physics
nav: Snapping Physics
description: Custom ScrollPhysics that always settle on an item boundary.
card: Custom ScrollPhysics that let any fixed-extent list snap cleanly to item boundaries on drag release or fling.
scripts: demos.js
---

A horizontal strip of cards where dragging feels completely ordinary while your finger is down, and releasing always settles cleanly onto a card boundary — advancing to the next card on a quick flick or snapping back to the nearest one after a slow drag.

## Why Custom `ScrollPhysics`?

Flutter ships `PageScrollPhysics` for `PageView`, where every page is as wide as the viewport (`viewportDimension * viewportFraction`). As soon as your items are narrower than the viewport — say a strip of `220px` cards inside a `400px` screen — `PageScrollPhysics` snaps to viewport multiples instead of card multiples.

You could try listening to `ScrollEndNotification` and calling `controller.animateTo(...)` after every scroll finishes. That approach fights the framework: the list decelerates under standard friction first, comes to a stop, and then jerks into a second animation. Custom `ScrollPhysics` replace the ballistic simulation *at the moment the finger lifts*, so the card glides into place in one continuous spring motion with the user's release velocity preserved.

## Try it Out

Drag the strip left or right, flick it quickly, or switch between `SnapScrollPhysics` and plain clamping physics to feel the difference when you let go.

<div class="demo" data-demo="snapping">
<div class="demo-stage">
<div class="demo-view"><canvas width="320" height="180"></canvas></div>
<div class="demo-side">
<div class="demo-heading">Live ScrollPosition</div>
<table class="demo-readout">
<tr><td>pixels</td><td data-f="pixels">0.0</td></tr>
<tr><td>velocity</td><td data-f="velocity">0 px/s</td></tr>
<tr><td>activity</td><td data-f="activity">idle</td></tr>
<tr><td>pixels / itemExtent</td><td data-f="item">0.00</td></tr>
<tr><td>targetPixels</td><td class="hot" data-f="target">0.0</td></tr>
</table>
</div>
</div>
<div class="demo-controls">
<label>Physics</label>
<button class="demo-btn on" type="button" data-mode="snap">SnapScrollPhysics</button>
<button class="demo-btn" type="button" data-mode="clamp">ClampingScrollPhysics</button>
<span class="demo-spacer"></span>
<button class="demo-btn" type="button" data-action="fling">Fling +1 →</button>
</div>
<div class="demo-note">Drag or use a trackpad/wheel. With snapping on, releasing launches a single spring toward <code>targetPixels</code>.</div>
</div>

## The Implementation

### Preserving the Physics Chain with `applyTo`

`Scrollable` never uses your `ScrollPhysics` object directly. It merges the widget's physics with the ambient `ScrollBehavior` physics by calling `physics.applyTo(ambientPhysics)`. The base `ScrollPhysics.applyTo` returns a plain `ScrollPhysics`, so if you forget to override `applyTo`, your subclass is silently discarded before the first frame.

```dart
@override
SnapScrollPhysics applyTo(ScrollPhysics? ancestor) {
  return SnapScrollPhysics(
    itemExtent: itemExtent,
    parent: buildParent(ancestor),
  );
}

@override
bool shouldUpdate(covariant SnapScrollPhysics old) {
  return itemExtent != old.itemExtent || super.shouldUpdate(old);
}
```

`buildParent(ancestor)` chains `ancestor` onto any existing `parent` already attached to your instance. Overriding `shouldUpdate` tells `ScrollableState` to rebuild the merged chain if the caller rebuilds with a different `itemExtent`.

### Choosing the Landing Offset

When the finger lifts, `pixels / itemExtent` gives the fractional item index currently aligned with the leading edge. A slow release rounds to the nearest integer. A flick whose speed exceeds `tolerance.velocity` nudges that fractional index by `0.5` in the fling direction before rounding, which guarantees advancing to the next card even if the finger barely crossed `10%` of the card width.

```dart
double _targetPixels(
  ScrollMetrics position,
  Tolerance tolerance,
  double velocity,
) {
  double item = position.pixels / itemExtent;
  // A fling commits to the next item in its direction, however short the
  // drag was. Without a fling, the nearest item wins.
  if (velocity < -tolerance.velocity) {
    item -= 0.5;
  } else if (velocity > tolerance.velocity) {
    item += 0.5;
  }
  return clampDouble(
    item.roundToDouble() * itemExtent,
    position.minScrollExtent,
    position.maxScrollExtent,
  );
}
```

Clamping to `[minScrollExtent, maxScrollExtent]` ensures the last card never snaps past the end of the content when the viewport holds multiple cards at once.

### Returning the Ballistic Simulation

`createBallisticSimulation` runs whenever the position enters a ballistic phase — right after a drag ends, after content dimensions change, or at the end of `jumpTo`. Two edge cases keep the physics feeling native:

1. If the user is already overscrolled at either end and moving *away* from the list, delegate to `super.createBallisticSimulation` so the platform's own bounce or clamp handles the edge.
2. If `target == position.pixels`, return `null` so the position transitions straight to `IdleScrollActivity` without scheduling a zero-distance animation controller tick.

```dart
@override
Simulation? createBallisticSimulation(
  ScrollMetrics position,
  double velocity,
) {
  // Out of range and not heading back in: let the parent physics bring the
  // position back, exactly as it would without snapping.
  if ((velocity <= 0.0 && position.pixels <= position.minScrollExtent) ||
      (velocity >= 0.0 && position.pixels >= position.maxScrollExtent)) {
    return super.createBallisticSimulation(position, velocity);
  }
  final Tolerance tolerance = toleranceFor(position);
  final double target = _targetPixels(position, tolerance, velocity);
  if (target != position.pixels) {
    return ScrollSpringSimulation(
      spring,
      position.pixels,
      target,
      velocity,
      tolerance: tolerance,
    );
  }
  // Already resting on an item boundary: nothing to simulate.
  return null;
}
```

Passing the user's release `velocity` into `ScrollSpringSimulation` is what makes a fast flick arrive briskly without a visible hitch at liftoff.

## Full Source Code

```dart
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

/// Scroll physics that always come to rest on an item boundary.
///
/// Works with any scrollable whose items all share one main-axis extent, for
/// example a [ListView] with `itemExtent` set.
class SnapScrollPhysics extends ScrollPhysics {
  const SnapScrollPhysics({required this.itemExtent, super.parent})
    : assert(itemExtent > 0);

  /// The main-axis extent of every item.
  final double itemExtent;

  // Without this override, combining these physics with the platform's
  // physics would return a plain ScrollPhysics and the snapping would vanish.
  @override
  SnapScrollPhysics applyTo(ScrollPhysics? ancestor) {
    return SnapScrollPhysics(
      itemExtent: itemExtent,
      parent: buildParent(ancestor),
    );
  }

  // Lets a Scrollable know that a rebuilt instance carries a new itemExtent.
  @override
  bool shouldUpdate(covariant SnapScrollPhysics old) {
    return itemExtent != old.itemExtent || super.shouldUpdate(old);
  }

  double _targetPixels(
    ScrollMetrics position,
    Tolerance tolerance,
    double velocity,
  ) {
    double item = position.pixels / itemExtent;
    // A fling commits to the next item in its direction, however short the
    // drag was. Without a fling, the nearest item wins.
    if (velocity < -tolerance.velocity) {
      item -= 0.5;
    } else if (velocity > tolerance.velocity) {
      item += 0.5;
    }
    return clampDouble(
      item.roundToDouble() * itemExtent,
      position.minScrollExtent,
      position.maxScrollExtent,
    );
  }

  @override
  Simulation? createBallisticSimulation(
    ScrollMetrics position,
    double velocity,
  ) {
    // Out of range and not heading back in: let the parent physics bring the
    // position back, exactly as it would without snapping.
    if ((velocity <= 0.0 && position.pixels <= position.minScrollExtent) ||
        (velocity >= 0.0 && position.pixels >= position.maxScrollExtent)) {
      return super.createBallisticSimulation(position, velocity);
    }
    final Tolerance tolerance = toleranceFor(position);
    final double target = _targetPixels(position, tolerance, velocity);
    if (target != position.pixels) {
      return ScrollSpringSimulation(
        spring,
        position.pixels,
        target,
        velocity,
        tolerance: tolerance,
      );
    }
    // Already resting on an item boundary: nothing to simulate.
    return null;
  }
}

/// A horizontal strip of cards that snaps to each card.
class SnappingCards extends StatelessWidget {
  const SnappingCards({super.key, this.controller, this.itemCount = 12});

  static const double itemExtent = 220.0;

  final ScrollController? controller;
  final int itemCount;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      controller: controller,
      scrollDirection: Axis.horizontal,
      physics: const SnapScrollPhysics(itemExtent: itemExtent),
      itemExtent: itemExtent,
      itemCount: itemCount,
      itemBuilder: (BuildContext context, int index) {
        return Padding(
          padding: const EdgeInsets.all(8.0),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: Color.lerp(
                const Color(0xFF5B8DEE),
                const Color(0xFF7A4DF0),
                index / itemCount,
              ),
              borderRadius: BorderRadius.circular(16.0),
            ),
            child: Center(
              child: Text(
                '$index',
                style: const TextStyle(
                  color: Color(0xFFFFFFFF),
                  fontSize: 40.0,
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
```

## Similar Implementations

- `PageScrollPhysics` in `package:flutter/src/widgets/page_view.dart` uses the exact same `±0.5` velocity bias, scaled by `position.viewportDimension * viewportFraction` instead of a fixed `itemExtent`.
- `FixedExtentScrollPhysics` in `package:flutter/src/widgets/list_wheel_scroll_view.dart` snaps cylindrical wheel pickers (`CupertinoPicker`) to integer item indices.
