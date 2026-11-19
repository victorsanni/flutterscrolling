---
title: createScrollPosition()
nav: createScrollPosition()
description: Override createScrollPosition() in a custom ScrollController to customize position initialization or subclass ScrollPosition.
---

The `createScrollPosition(ScrollPhysics physics, ScrollContext context, ScrollPosition? oldPosition)` method on `ScrollController` constructs the `ScrollPosition` owned by a mounting or updating `Scrollable`.

## Default Implementation

Constructs a standard `ScrollPositionWithSingleContext` seeded with `initialScrollOffset` and `keepScrollOffset`:

```dart
ScrollPosition createScrollPosition(
  ScrollPhysics physics,
  ScrollContext context,
  ScrollPosition? oldPosition,
) {
  return ScrollPositionWithSingleContext(
    physics: physics,
    context: context,
    initialPixels: initialScrollOffset,
    keepScrollOffset: keepScrollOffset,
    oldPosition: oldPosition,
    debugLabel: debugLabel,
  );
}
```

## Dynamic Initial Offset Computed at Mount Time

Example of a `ScrollController` subclass that computes its initial pixel offset dynamically (for instance from viewport-independent app state) whenever a new `Scrollable` attaches.

```dart
class DynamicInitialScrollController extends ScrollController {
  DynamicInitialScrollController({required this.initialOffsetBuilder});

  final double Function() initialOffsetBuilder;

  @override
  ScrollPosition createScrollPosition(
    ScrollPhysics physics,
    ScrollContext context,
    ScrollPosition? oldPosition,
  ) {
    return ScrollPositionWithSingleContext(
      physics: physics,
      context: context,
      initialPixels: initialOffsetBuilder(),
      keepScrollOffset: keepScrollOffset,
      oldPosition: oldPosition,
      debugLabel: debugLabel,
    );
  }
}
```

## Synchronize Initial Offset With a Sibling Controller

Example where a secondary `ListView` starts at the exact current `offset` of an already-mounted primary `ScrollController` when swapped onto screen.

```dart
class MirrorStartController extends ScrollController {
  MirrorStartController({required this.leader});

  final ScrollController leader;

  @override
  ScrollPosition createScrollPosition(
    ScrollPhysics physics,
    ScrollContext context,
    ScrollPosition? oldPosition,
  ) {
    return ScrollPositionWithSingleContext(
      physics: physics,
      context: context,
      initialPixels: leader.hasClients ? leader.offset : initialScrollOffset,
      keepScrollOffset: false,
      oldPosition: oldPosition,
    );
  }
}
```
