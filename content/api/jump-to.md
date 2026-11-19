---
title: jumpTo()
nav: jumpTo()
description: Use jumpTo() on ScrollController or ScrollPosition to teleport immediately to an exact pixel offset.
---

The `jumpTo(double value)` method cancels any active drag or ballistic fling, moves `pixels` straight to `value` without animation, dispatches start/update/end scroll notifications if `pixels` changed, and runs `goBallistic(0.0)` so an out-of-range jump still settles cleanly.

## Default Implementation

On `ScrollController`, `jumpTo` forwards the call to every attached `ScrollPosition`:

```dart
void jumpTo(double value) {
  assert(_positions.isNotEmpty, 'ScrollController not attached to any scroll views.');
  for (final ScrollPosition position in List<ScrollPosition>.of(_positions)) {
    position.jumpTo(value);
  }
}
```

## Jump Back to the Top

Example that teleports to the leading edge only when a scrollable is mounted and attached.

```dart
if (controller.hasClients) {
  controller.jumpTo(controller.position.minScrollExtent);
}
```

## Jump to the Very Bottom After Layout

Example that jumps to `maxScrollExtent` on the first frame after new items are added, when `maxScrollExtent` has been updated by layout.

```dart
WidgetsBinding.instance.addPostFrameCallback((_) {
  if (controller.hasClients) {
    controller.jumpTo(controller.position.maxScrollExtent);
  }
});
```

## Jump to a Fixed-Extent Item Index

Example where every row in a `ListView` has `itemExtent: 56.0`, clamped so indices near the end do not jump past `maxScrollExtent`.

```dart
void jumpToIndex(ScrollController controller, int index, double itemExtent) {
  if (!controller.hasClients) {
    return;
  }
  final ScrollPosition pos = controller.position;
  final double target = (index * itemExtent).clamp(
    pos.minScrollExtent,
    pos.maxScrollExtent,
  );
  controller.jumpTo(target);
}
```
