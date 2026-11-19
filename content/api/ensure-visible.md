---
title: Scrollable.ensureVisible()
nav: ensureVisible()
description: Use Scrollable.ensureVisible() to scroll any mounted BuildContext into the visible viewport window.
---

`Scrollable.ensureVisible` walks up every enclosing `Scrollable` from a target `BuildContext` and scrolls each one so the target's `RenderObject` becomes visible inside the viewport.

- The target widget **must currently be mounted** (built and laid out in the tree).
- Respects `maxScrollObstructionExtent` reported by pinned slivers like `PinnedHeaderSliver` and `SliverAppBar(pinned: true)`.

## Signature and Defaults

With default arguments, `ensureVisible` jumps immediately (`Duration.zero`) and aligns the target with the viewport's leading edge (`alignment: 0.0`):

```dart
static Future<void> ensureVisible(
  BuildContext context, {
  double alignment = 0.0,
  Duration duration = Duration.zero,
  Curve curve = Curves.ease,
  ScrollPositionAlignmentPolicy alignmentPolicy = ScrollPositionAlignmentPolicy.explicit,
})
```

## Center a Keyed Section Widget Smoothly

Example that centers a mounted form error or section header (`alignment: 0.5`) inside the viewport.

```dart
final BuildContext? target = sectionKey.currentContext;
if (target != null) {
  await Scrollable.ensureVisible(
    target,
    alignment: 0.5,
    duration: const Duration(milliseconds: 250),
    curve: Curves.easeOutCubic,
  );
}
```

## Reveal Only If Clipped Below the Bottom Edge

Example for keyboard down-arrow selection: leaves the scroll offset untouched if the row is already fully visible, and scrolls just far enough to show its bottom edge if clipped.

```dart
await Scrollable.ensureVisible(
  rowContext,
  alignmentPolicy: ScrollPositionAlignmentPolicy.keepVisibleAtEnd,
  duration: const Duration(milliseconds: 150),
  curve: Curves.easeOut,
);
```

## Reveal Only If Clipped Above the Top Edge

Example for keyboard up-arrow selection: scrolls up just far enough to clear the leading edge (and any pinned header) if the row sits above the visible area.

```dart
await Scrollable.ensureVisible(
  rowContext,
  alignmentPolicy: ScrollPositionAlignmentPolicy.keepVisibleAtStart,
  duration: const Duration(milliseconds: 150),
  curve: Curves.easeOut,
);
```
