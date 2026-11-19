// Example 1: scroll physics that always come to rest on an item boundary.
//
// Walkthrough: site/examples/snapping-physics.html

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
