---
title: animateTo()
nav: animateTo()
description: Use animateTo() on ScrollController or ScrollPosition to smoothly drive pixels along a curve over a fixed duration.
---

The `animateTo(double offset, {required Duration duration, required Curve curve})` method starts a `DrivenScrollActivity` from the current `pixels` to `offset` and returns a `Future<void>` that completes when the animation finishes (or is interrupted by another gesture or activity).

## Default Implementation

On `ScrollController`, `animateTo` starts an animation on every attached `ScrollPosition` and waits for all of them with `Future.wait`:

```dart
Future<void> animateTo(
  double offset, {
  required Duration duration,
  required Curve curve,
}) async {
  assert(_positions.isNotEmpty, 'ScrollController not attached to any scroll views.');
  await Future.wait<void>(<Future<void>>[
    for (int i = 0; i < _positions.length; i += 1)
      _positions[i].animateTo(offset, duration: duration, curve: curve),
  ]);
}
```

## Smooth Scroll to Top

Example that animates back to `0.0` with an ease-out curve when the user taps a floating button.

```dart
Future<void> scrollToTop(ScrollController controller) async {
  if (!controller.hasClients) {
    return;
  }
  await controller.animateTo(
    0.0,
    duration: const Duration(milliseconds: 320),
    curve: Curves.easeOutCubic,
  );
}
```

## Cap Travel Time on Very Long Lists

Example that jumps near the destination first when `pixels` is thousands of pixels away, then animates only the final two screenfuls so the user never sees a blurry 60-item flash.

```dart
Future<void> smartScrollToTop(ScrollController controller) async {
  if (!controller.hasClients) {
    return;
  }
  final double maxRunup = controller.position.viewportDimension * 2.0;
  if (controller.offset > maxRunup) {
    controller.jumpTo(maxRunup);
  }
  await controller.animateTo(
    0.0,
    duration: const Duration(milliseconds: 280),
    curve: Curves.easeOutCubic,
  );
}
```

## Respect Reduced-Motion Accessibility Preferences

Example that switches from `animateTo` to an instant `jumpTo` when the user has enabled system reduced motion.

```dart
Future<void> scrollToOffset(BuildContext context, ScrollController controller, double target) async {
  if (!controller.hasClients) {
    return;
  }
  if (MediaQuery.disableAnimationsOf(context)) {
    controller.jumpTo(target);
    return;
  }
  await controller.animateTo(
    target,
    duration: const Duration(milliseconds: 250),
    curve: Curves.easeInOut,
  );
}
```
