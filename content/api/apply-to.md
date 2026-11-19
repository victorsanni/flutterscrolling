---
title: applyTo()
nav: applyTo()
description: Implement applyTo() in a custom ScrollPhysics subclass to preserve your physics in the chain.
---

The `applyTo(ScrollPhysics? ancestor)` method clones your `ScrollPhysics` subclass with `ancestor` chained onto the end of its `parent` list. `Scrollable` calls `applyTo` whenever it merges widget-level physics with ambient `ScrollBehavior` physics.

## Default Implementation

The base `ScrollPhysics.applyTo` returns a plain `ScrollPhysics` instance, which drops any subclass overrides if you forget to override it:

```dart
ScrollPhysics applyTo(ScrollPhysics? ancestor) {
  return ScrollPhysics(parent: buildParent(ancestor));
}
```

## Stateless Subclass - No Extra Fields

Example where your `ScrollPhysics` subclass has no constructor parameters beyond `super.parent`. Always compute `parent:` via `buildParent(ancestor)` rather than passing `ancestor` directly so existing parents on `this` are preserved.

```dart
class FastFlingPhysics extends ScrollPhysics {
  const FastFlingPhysics({super.parent});

  @override
  FastFlingPhysics applyTo(ScrollPhysics? ancestor) {
    return FastFlingPhysics(parent: buildParent(ancestor));
  }
}
```

## Parameterized Subclass - Copy Fields and Implement `shouldUpdate`

Example where your `ScrollPhysics` subclass carries configuration fields. Copy every field in `applyTo` and compare them in `shouldUpdate` so `ScrollableState` rebuilds the physics chain when a parameter changes.

```dart
class SnapScrollPhysics extends ScrollPhysics {
  const SnapScrollPhysics({required this.itemExtent, super.parent});

  final double itemExtent;

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
}
```

## Composing Two Physics Classes at a Call Site

Example of chaining two built-in `ScrollPhysics` instances from widget code. Either pass `parent:` in a `const` constructor or call `applyTo` dynamically.

```dart
// Const composition: BouncingScrollPhysics runs first, AlwaysScrollableScrollPhysics second.
const ScrollPhysics physics = BouncingScrollPhysics(
  parent: AlwaysScrollableScrollPhysics(),
);
```
