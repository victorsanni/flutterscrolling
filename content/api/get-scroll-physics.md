---
title: getScrollPhysics()
nav: getScrollPhysics()
description: Override getScrollPhysics() on ScrollBehavior (or use copyWith) to set default ScrollPhysics for a subtree or app.
---

The `getScrollPhysics(BuildContext context)` method on `ScrollBehavior` supplies the ambient `ScrollPhysics` chain for every `Scrollable` in a `ScrollConfiguration` subtree.

- When a `ScrollView` passes an explicit `physics:`, `ScrollableState` runs `widget.physics!.applyTo(scrollBehavior.getScrollPhysics(context))`.
- When `physics:` is null, `ScrollableState` uses `scrollBehavior.getScrollPhysics(context)` directly.

## Default Implementation

Base `ScrollBehavior` switches on `getPlatform(context)` (`defaultTargetPlatform`), pairing `BouncingScrollPhysics` on Apple platforms and `ClampingScrollPhysics` everywhere else with `RangeMaintainingScrollPhysics` as the parent:

```dart
ScrollPhysics getScrollPhysics(BuildContext context) {
  switch (getPlatform(context)) {
    case TargetPlatform.iOS:
    case TargetPlatform.macOS:
      return const BouncingScrollPhysics(parent: RangeMaintainingScrollPhysics());
    case TargetPlatform.android:
    case TargetPlatform.fuchsia:
    case TargetPlatform.linux:
    case TargetPlatform.windows:
      return const ClampingScrollPhysics(parent: RangeMaintainingScrollPhysics());
  }
}
```

## Force iOS-Style Bounce Across All Platforms (`copyWith`)

Example that applies `BouncingScrollPhysics` across Android, desktop, and web in `MaterialApp` without writing a subclass.

```dart
MaterialApp(
  scrollBehavior: const MaterialScrollBehavior().copyWith(
    physics: const BouncingScrollPhysics(
      parent: RangeMaintainingScrollPhysics(),
    ),
  ),
  home: const HomePage(),
)
```

## Subclass `MaterialScrollBehavior` for Custom App-Wide Physics

Example when your physics depend on `BuildContext` (for instance disabling overscroll bounce when accessibility reduced motion is active).

```dart
class AccessibleScrollBehavior extends MaterialScrollBehavior {
  const AccessibleScrollBehavior();

  @override
  ScrollPhysics getScrollPhysics(BuildContext context) {
    if (MediaQuery.disableAnimationsOf(context)) {
      return const ClampingScrollPhysics(
        parent: RangeMaintainingScrollPhysics(),
      );
    }
    return super.getScrollPhysics(context);
  }
}
```

## Override Physics Locally for One Subtree

Example wrapping a single screen or panel in `ScrollConfiguration` while keeping the surrounding app's scrollbars and overscroll indicators intact.

```dart
ScrollConfiguration(
  behavior: ScrollConfiguration.of(context).copyWith(
    physics: const ClampingScrollPhysics(
      parent: RangeMaintainingScrollPhysics(),
    ),
  ),
  child: child,
)
```
