---
title: ScrollMetrics
nav: ScrollMetrics
description: Read ScrollMetrics properties on ScrollPosition, ScrollNotification, and ScrollPhysics callbacks.
---

`ScrollMetrics` is the read-only interface describing a scroll view's current offset, bounds, and window size. Both `ScrollPosition` (live, mutable) and `FixedScrollMetrics` (the immutable snapshot carried inside `ScrollNotification.metrics`) implement `ScrollMetrics`.

## Core Fields and Derived Getters

| Member | Type | Meaning |
| --- | --- | --- |
| `pixels` | `double` | Current scroll offset relative to origin |
| `minScrollExtent` | `double` | Smallest in-range offset (`0.0` in standard forward lists) |
| `maxScrollExtent` | `double` | Largest in-range offset (`0.0` when all content fits in viewport) |
| `viewportDimension` | `double` | Main-axis length of the viewport window |
| `axisDirection` / `axis` | `AxisDirection` / `Axis` | Direction in which `pixels` increases |
| `extentBefore` | `double` | `max(pixels - minScrollExtent, 0.0)` |
| `extentInside` | `double` | Visible slice of in-range content inside viewport |
| `extentAfter` | `double` | `max(maxScrollExtent - pixels, 0.0)` |
| `extentTotal` | `double` | `maxScrollExtent - minScrollExtent + viewportDimension` |
| `outOfRange` | `bool` | `pixels < minScrollExtent \|\| pixels > maxScrollExtent` |
| `atEdge` | `bool` | `pixels == minScrollExtent \|\| pixels == maxScrollExtent` |

## Compute Safe `0.0..1.0` Scroll Progress

Example that converts `ScrollMetrics` into a clamped progress fraction without dividing by zero when all content fits on screen.

```dart
double scrollProgress(ScrollMetrics metrics) {
  final double range = metrics.maxScrollExtent - metrics.minScrollExtent;
  if (range <= 0.0) {
    return 0.0;
  }
  return ((metrics.pixels - metrics.minScrollExtent) / range).clamp(0.0, 1.0);
}
```

## Detect Near-Bottom Pagination Threshold

Example that checks `extentAfter` so infinite-scroll prefetching triggers `300px` before the user hits the end.

```dart
bool shouldLoadMore(ScrollMetrics metrics) {
  return metrics.maxScrollExtent > 0.0 && metrics.extentAfter < 300.0;
}
```

## Guard `ScrollPosition` Reads Before First Layout

Example of checking `hasContentDimensions` and `hasPixels` on a live `ScrollPosition` when reading outside a notification callback.

```dart
bool isScrolled(ScrollController controller) {
  if (!controller.hasClients) {
    return false;
  }
  final ScrollPosition pos = controller.position;
  return pos.hasPixels && pos.hasContentDimensions && pos.pixels > pos.minScrollExtent;
}
```
