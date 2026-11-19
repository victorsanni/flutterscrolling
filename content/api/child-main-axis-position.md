---
title: childMainAxisPosition()
nav: childMainAxisPosition()
description: Implement childMainAxisPosition() in a custom RenderSliver to align painting, hit testing, and coordinate transforms.
---

The `childMainAxisPosition(covariant RenderObject child)` method returns a child's main-axis paint position relative to the sliver's own zero point (`constraints.scrollOffset` inside the sliver).

`RenderSliverSingleBoxAdapter` and `RenderSliverMultiBoxAdaptor` read `childMainAxisPosition` in three places — `paint`, `hitTestBoxChild`, and `applyPaintTransform` — so overriding this one method keeps drawing and pointer hits automatically synchronized.

## Default Implementation

On the base `RenderSliver`, calling `childMainAxisPosition` asserts and throws unless overridden:

```dart
double childMainAxisPosition(covariant RenderObject child) {
  assert(() {
    throw FlutterError.fromParts(<DiagnosticsNode>[
      ErrorSummary('${objectRuntimeType(this, 'RenderSliver')} does not implement childMainAxisPosition.'),
    ]);
  }());
  return 0.0;
}
```

## Normal Scrolling Single Box (`-constraints.scrollOffset`)

Example used by `RenderSliverToBoxAdapter`: as `constraints.scrollOffset` increases, the child slides off the leading edge by that exact distance (and `setChildParentData` writes the matching `paintOffset` onto `SliverPhysicalParentData`).

```dart
@override
double childMainAxisPosition(RenderBox child) => -constraints.scrollOffset;
```

## Pinned Header Single Box (`0.0`)

Example used by `PinnedHeaderSliver` and [Sticky Header](/examples/sticky-header): the child never slides past the sliver's leading edge, remaining anchored at `0.0` (shifted by `geometry.paintOrigin` if earlier headers overlap).

```dart
@override
double childMainAxisPosition(RenderBox child) => 0.0;
```

## Multi-Child List Item (`layoutOffset - constraints.scrollOffset`)

Example used by `RenderSliverMultiBoxAdaptor` (`SliverList` / `SliverGrid`): each child stores its content-space start offset in `SliverMultiBoxAdaptorParentData.layoutOffset`, and subtracting `constraints.scrollOffset` converts that into viewport-relative coordinates.

```dart
@override
double childMainAxisPosition(RenderBox child) {
  final SliverMultiBoxAdaptorParentData childParentData =
      child.parentData! as SliverMultiBoxAdaptorParentData;
  return childParentData.layoutOffset! - constraints.scrollOffset;
}
```
