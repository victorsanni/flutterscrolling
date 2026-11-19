---
title: Two-Dimensional Scrolling
nav: 2D Scrolling
description: How TwoDimensionalScrollView, TwoDimensionalScrollable, and RenderTwoDimensionalViewport virtualize both axes without slivers.
---

This guide walks experienced Flutter developers through Flutter's 2D scrolling foundation: `TwoDimensionalScrollView`, `TwoDimensionalScrollable`, `TwoDimensionalViewport`, and `ChildVicinity`. By the end, you'll understand why slivers are strictly one-dimensional, how Flutter wires two perpendicular `ScrollPosition`s into a single viewport, and how `layoutChildSequence` virtualizes a 10,000 × 10,000 grid in $O(\text{visible cells})$. We'll skip `two_dimensional_scrollables` package styling options — this is about the core framework architecture, and only that architecture.

## What This Guide Covers

- **Why Slivers Can't Virtualize Two Axes at Once** — What goes wrong when you nest horizontal `ListView`s inside a vertical `ListView`.
- **Two `Scrollable`s, One `TwoDimensionalViewport`** — How `TwoDimensionalScrollable` pairs a vertical `ScrollPosition` and a horizontal `ScrollPosition`.
- **`DiagonalDragBehavior`** — Controlling whether diagonal finger drags pan freely, lock to the first axis, or lock per gesture.
- **Addressing Cells with `ChildVicinity`** — Replacing 1D `int index` with `(xIndex, yIndex)` inside `TwoDimensionalChildDelegate`.
- **How `RenderTwoDimensionalViewport` Works** — Building, positioning, and garbage-collecting `RenderBox` cells in `layoutChildSequence`.
- **When to Use `two_dimensional_scrollables` Instead of Subclassing** — `TableView` and `TreeView` built on top of these primitives.

## Why Slivers Can't Virtualize Two Axes at Once

Look back at `SliverConstraints`: it has *one* `scrollOffset`, *one* `remainingPaintExtent`, and *one* fixed `crossAxisExtent`. Slivers are 1D by design.

If you fake a spreadsheet by putting a horizontal `SingleChildScrollView` around a vertical `ListView`, every row builds *all* of its columns eagerly; if you put a horizontal `ListView` inside each vertical row, each row scrolls horizontally on its own instead of moving the whole table together! True 2D virtualization needs **one viewport** that knows both `horizontalOffset.pixels` and `verticalOffset.pixels` at the same time.

## Two `Scrollable`s, One `TwoDimensionalViewport`

Open `two_dimensional_scrollable.dart` and you'll find a remarkably clean reuse of the 1D machinery you already learned:

`TwoDimensionalScrollable` simply nests **two ordinary `Scrollable` widgets** — an outer vertical `Scrollable` and an inner horizontal `Scrollable` — and hands *both* of their `ViewportOffset`s (`verticalOffset` and `horizontalOffset`) into a single `TwoDimensionalViewport`:

```dart
// Conceptual structure inside TwoDimensionalScrollable.build:
Scrollable(
  axisDirection: verticalAxis,
  controller: verticalDetails.controller,
  physics: verticalDetails.physics,
  viewportBuilder: (BuildContext context, ViewportOffset verticalOffset) {
    return Scrollable(
      axisDirection: horizontalAxis,
      controller: horizontalDetails.controller,
      physics: horizontalDetails.physics,
      viewportBuilder: (BuildContext context, ViewportOffset horizontalOffset) {
        return viewportBuilder(context, verticalOffset, horizontalOffset);
      },
    );
  },
)
```

Because both axes are driven by real `Scrollable`s, you reuse standard `ScrollController`s, `BouncingScrollPhysics` / `ClampingScrollPhysics`, `Scrollbar`s, and `ScrollNotification`s on each axis without reinventing any gesture or physics code!

## `DiagonalDragBehavior`

When two perpendicular `Scrollable`s wrap the same surface, what should happen when a user drags their finger at a `35°` diagonal? `TwoDimensionalScrollView.diagonalDragBehavior` offers four built-in modes:

- **`DiagonalDragBehavior.none`** (default) — Only one axis wins any single drag gesture; dragging mostly vertically scrolls only vertically until you lift your finger.
- **`DiagonalDragBehavior.weightedEvent`** — Locks to horizontal or vertical per pointer-move sample based on the dominant delta.
- **`DiagonalDragBehavior.weightedContinuous`** — Locks to the initial dominant axis unless the user sharply changes direction mid-drag.
- **`DiagonalDragBehavior.free`** — Both `VerticalDragGestureRecognizer` and `HorizontalDragGestureRecognizer` accept the gesture simultaneously, panning smoothly across `(x, y)` like a map or infinite canvas.

## Addressing Cells with `ChildVicinity`

Because there are no slivers inside a `TwoDimensionalViewport`, cells are plain `RenderBox` widgets addressed by a 2D coordinate struct called `ChildVicinity`:

```dart
const ChildVicinity cell = ChildVicinity(xIndex: 4, yIndex: 12);
```

`TwoDimensionalChildBuilderDelegate` (the 2D twin of `SliverChildBuilderDelegate`) builds widgets on demand for `(BuildContext context, ChildVicinity vicinity)`, bounded optionally by `maxXIndex` and `maxYIndex`.

## How `RenderTwoDimensionalViewport` Works

In the Flutter SDK itself, `TwoDimensionalScrollView`, `TwoDimensionalViewport`, and `RenderTwoDimensionalViewport` are **abstract base classes**. To define a concrete 2D layout (fixed grid, variable spreadsheet with pinned row/column headers, or staggered canvas), a subclass implements one method on `RenderTwoDimensionalViewport`: **`layoutChildSequence()`**.

Inside `layoutChildSequence()`, your viewport does four things:

1. Reads `horizontalOffset.pixels`, `verticalOffset.pixels`, `viewportDimension` (`Size`), and `cacheExtent` to decide which `(xIndex, yIndex)` cells fall inside the visible + cache rectangle.
2. Calls `buildOrObtainChildFor(ChildVicinity(xIndex: x, yIndex: y))` for only those visible cells (which builds new widgets mid-layout via `invokeLayoutCallback` or reuses mounted ones).
3. Lays out each obtained `RenderBox` child and sets `parentDataOf(child).layoutOffset = Offset(cellX - horizontalOffset.pixels, cellY - verticalOffset.pixels)`.
4. Reports total 2D bounds via `verticalOffset.applyContentDimensions(...)` and `horizontalOffset.applyContentDimensions(...)`.

Any previously mounted cell that was *not* visited by `buildOrObtainChildFor` during `layoutChildSequence()` is **automatically garbage-collected** (or parked in the keep-alive bucket) by `RenderTwoDimensionalViewport.performLayout` right after `layoutChildSequence()` returns!

## When to Use `two_dimensional_scrollables` Instead of Subclassing

You only need to subclass `TwoDimensionalScrollView` and `RenderTwoDimensionalViewport` yourself when inventing a novel 2D spatial layout (such as an infinite node graph, hex map, or custom timeline gantt chart).

For data tables, spreadsheets with pinned rows and columns, or lazy 2D tree views, the Flutter team's official `package:two_dimensional_scrollables` provides ready-to-use `TableView` and `TreeView` widgets built directly on `RenderTwoDimensionalViewport`.

## Mental Model Summary

- **Slivers are 1D; `TwoDimensionalViewport` skips slivers completely** and manages `RenderBox` children directly by `ChildVicinity(xIndex, yIndex)`.
- **Two standard `Scrollable`s** drive `verticalOffset` and `horizontalOffset` independently, coordinated by `DiagonalDragBehavior`.
- **`layoutChildSequence()`** visits only cells inside the 2D visible + cache window; unvisited cells are garbage-collected automatically at the end of every layout pass.

That completes every guide on this site. To see custom physics, a custom viewport, and a custom sliver written out line by line with live interactive demos, head to the [Examples](/examples) next.
