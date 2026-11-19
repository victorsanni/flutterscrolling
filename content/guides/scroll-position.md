---
title: Scroll Position
nav: Scroll Position
description: The one number that scrolling is about, the extents around it, and who is allowed to change it.
card: Understand pixels, minScrollExtent, maxScrollExtent, and why setPixels, correctPixels, and forcePixels exist separately.
---

This guide walks experienced Flutter developers through `ScrollPosition` and the `ScrollMetrics` values it maintains. By the end, you'll understand what `pixels`, `minScrollExtent`, `maxScrollExtent`, and `viewportDimension` mean geometrically, when they become valid, and why the framework has three separate internal methods for changing `pixels`. We'll skip gesture recognizers, sliver layout internals, and multi-scroll controllers — this is about the position object, and only the position object.

## What This Guide Covers

- **What `ScrollPosition` Actually Is** — How `ViewportOffset`, `ScrollMetrics`, and `ScrollPositionWithSingleContext` relate.
- **The Extents Around `pixels`** — How `minScrollExtent`, `maxScrollExtent`, `viewportDimension`, and the `extentBefore` / `extentInside` / `extentAfter` getters fit together.
- **Three Ways `pixels` Changes** — The sharp contract difference between `setPixels`, `correctPixels`, and `forcePixels`.
- **The Dimension Handshake** — What happens during layout when the viewport reports new window or content sizes.
- **Common Pitfalls** — Reading `pixels` before first layout, mutating state during `correctBy`, and confusing `atEdge` with overscroll.

## What `ScrollPosition` Actually Is

`ScrollPosition` is the long-lived `ChangeNotifier`-style object (inheriting from `ViewportOffset` and mixing in `ScrollMetrics`) that owns the current scroll offset of a single `Scrollable`.

In nearly every scroll view you use — `ListView`, `GridView`, `CustomScrollView`, `SingleChildScrollView`, `PageView` — the concrete runtime type of `controller.position` is `ScrollPositionWithSingleContext`. Only specialized widgets that coordinate two viewports at once (such as `NestedScrollView`) substitute their own `ScrollPosition` subclass.

```dart
abstract class ScrollPosition extends ViewportOffset with ScrollMetrics {
  double get pixels;
  double get minScrollExtent;
  double get maxScrollExtent;
  double get viewportDimension;
  // ...
}
```

## The Extents Around `pixels`

A `ScrollPosition` describes a movable window (`viewportDimension`) sliding along a strip of content bounded by `minScrollExtent` and `maxScrollExtent`.

Suppose a vertical `ListView` is `300.0` pixels tall on screen (`viewportDimension == 300.0`), contains `960.0` pixels of total item height, and has been scrolled down by `180.0` pixels:

{{figure:scroll-extents|A 300px viewport scrolled 180px into 960px of total content: maxScrollExtent is 960 - 300 = 660.}}

Every convenience getter on `ScrollMetrics` derives directly from those four numbers:

| Property | Value in example | Formula |
| --- | --- | --- |
| `pixels` | `180.0` | Current offset from the content origin |
| `minScrollExtent` | `0.0` | Smallest in-range offset (`0.0` unless slivers exist before the center key) |
| `maxScrollExtent` | `660.0` | `960.0 - 300.0` (`0.0` when all content fits inside the viewport) |
| `viewportDimension` | `300.0` | Main-axis size of the viewport |
| `extentBefore` | `180.0` | `max(pixels - minScrollExtent, 0.0)` |
| `extentInside` | `300.0` | Visible slice of in-range content inside the viewport |
| `extentAfter` | `480.0` | `max(maxScrollExtent - pixels, 0.0)` |
| `outOfRange` | `false` | `pixels < minScrollExtent \|\| pixels > maxScrollExtent` |

Notice why `maxScrollExtent` is `660.0` and not `960.0`: when `pixels` reaches `660.0`, the bottom of the `300.0`-tall viewport aligns with `660.0 + 300.0 = 960.0`, the very end of the content. **If all content fits inside the viewport, `minScrollExtent` and `maxScrollExtent` are both `0.0`.**

> **Aside:** `minScrollExtent` is not always `0.0`. A `CustomScrollView` with a `center` key can grow slivers upward in the reverse direction, giving `minScrollExtent` a negative value such as `-400.0`. Always clamp against `minScrollExtent`, never against a hardcoded `0.0`.

## Three Ways `pixels` Changes

If you read `scroll_position.dart`, you'll find three methods that write to `_pixels`. Each exists for a different phase of the Flutter pipeline:

1. `setPixels(double newPixels)` is the normal path called on every frame of a drag, fling, or `animateTo`. It asks `physics.applyBoundaryConditions(this, newPixels)` how much of the move is refused, updates `_pixels`, calls `notifyListeners()`, dispatches `ScrollUpdateNotification` (and `OverscrollNotification` if anything was refused), and returns any refused overscroll to the caller.
2. `correctPixels(double value)` (and its relative helper `correctBy(double correction)`) mutates `_pixels` *silently* without calling `notifyListeners()`. **Only viewports call `correctPixels` or `correctBy`, and only during `performLayout`.** Firing listeners mid-layout would call `markNeedsLayout` on render objects currently being laid out, triggering framework assertions.
3. `forcePixels(double value)` sets `_pixels` unconditionally — bypassing `applyBoundaryConditions` — and schedules listener notifications. `jumpTo` and mouse-wheel jumps use `forcePixels` when they have already decided the exact destination.

```dart
// Inside RenderViewport.performLayout when a sliver reports a scrollOffsetCorrection:
offset.correctBy(geometry.scrollOffsetCorrection!); // silent: we are mid-layout!

// Inside DragScrollActivity / BallisticScrollActivity on a frame tick:
final double overscroll = position.setPixels(proposedPixels); // consults physics + notifies
```

Unless you are implementing a custom `Viewport` or a custom `ScrollActivity`, you never call these three methods directly. From app code, you call `jumpTo` or `animateTo` on `ScrollController` (or `ScrollPosition`), which wrap them safely.

## The Dimension Handshake

When a `ScrollPosition` is first constructed inside `ScrollableState`, it knows its `initialScrollOffset`, **but `hasViewportDimension` and `hasContentDimensions` are both `false`.** Reading `maxScrollExtent` or `viewportDimension` before the first layout throws a assertion error.

During `performLayout`, the viewport completes the handshake in order:

```dart
// 1. Tell the position how large the window is.
offset.applyViewportDimension(size.height);

// 2. Tell the position where scrollable content starts and ends.
//    Returns false if physics adjusted `pixels` and layout must re-run.
final bool stable = offset.applyContentDimensions(minExtent, maxExtent);
```

Inside `applyContentDimensions`, the position asks `physics.adjustPositionForNewDimensions(...)` where `pixels` should sit given the new bounds. By default, `RangeMaintainingScrollPhysics` lies at the end of every physics chain: if the content shrank so your old `pixels` of `800.0` now exceeds a new `maxScrollExtent` of `500.0` (while you aren't actively dragging), it silently corrects `pixels` to `500.0` and returns `false` so `RenderViewport` immediately runs another layout pass with the corrected offset.

## Common Pitfalls

**Reading `controller.position.maxScrollExtent` inside `initState`.** At `initState` time, no layout pass has happened yet — the controller isn't even attached to a `ScrollPosition`, and even inside a first-frame build `hasContentDimensions` is still `false`. Wait for `WidgetsBinding.instance.addPostFrameCallback` or check `position.hasContentDimensions` before reading extents.

**Assuming `pixels` is never negative.** On iOS and macOS, `BouncingScrollPhysics` lets `pixels` go negative when pulling past the top (`pixels == -42.0`) and above `maxScrollExtent` when pulling past the bottom. UI code that computes a `0.0..1.0` progress ratio from `pixels / maxScrollExtent` should clamp the result (and guard against `maxScrollExtent == 0.0` to avoid `NaN`).

**Confusing `atEdge` with overscroll.** `position.atEdge` is `true` only when `pixels == minScrollExtent || pixels == maxScrollExtent` *exactly*. The instant `pixels` bounces to `-0.5`, `atEdge` becomes `false` while `outOfRange` becomes `true`. Check `extentAfter == 0.0` when you want to know "at or past the trailing end."

That's `ScrollPosition` end to end: one `pixels` value framed by `minScrollExtent`, `maxScrollExtent`, and `viewportDimension`, updated loudly during input/animation and corrected silently during layout. Next, we'll look at `ScrollPhysics` — the object the position consults before every move.
