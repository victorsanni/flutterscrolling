---
title: Scroll Notifications
nav: Scroll Notifications
description: How scroll events bubble up the element tree, how depth tracks nested viewports, and why ScrollMetricsNotification is separate.
---

This guide walks experienced Flutter developers through `ScrollNotification`, `NotificationListener`, and `ScrollMetricsNotification`. By the end, you'll understand every notification type a scroll view emits, how `notification.depth` isolates nested scrollables, and when to prefer notifications over a `ScrollController` listener. We'll skip gesture arena mechanics and sliver geometry — this is about observing scroll events from above, and only that.

## What This Guide Covers

- **Why Notifications Exist Alongside Controllers** — Observing any descendant scrollable without passing a `ScrollController` down through ten widgets.
- **The Five `ScrollNotification` Subclasses** — Start, update, overscroll, end, and user-direction notifications.
- **Nested Scroll Views and `depth`** — How `ViewportElementMixin` increments `depth` so outer widgets ignore inner carousels.
- **`ScrollMetricsNotification` When Content Resizes** — Catching layout-driven extent changes that never move `pixels`.
- **Common Pitfalls** — Missing `depth == 0`, returning `true` by mistake, and calling `setState` on every pixel.

## Why Notifications Exist Alongside Controllers

A `ScrollController` works top-down: a parent creates it and hands it explicitly to one specific `ScrollView`. That breaks down as soon as a reusable wrapper widget — like `RefreshIndicator`, `Scrollbar`, or a collapsing app-bar shell — needs to observe *whatever* scrollable the caller placed inside its `child` subtree.

`ScrollNotification` works bottom-up. Whenever a `ScrollPosition` starts, moves, overscrolls, or stops, it dispatches a notification from its `Scrollable`'s `BuildContext` that bubbles up every ancestor `Element` until it hits the root or a `NotificationListener` returns `true`.

```dart
NotificationListener<ScrollNotification>(
  onNotification: (ScrollNotification notification) {
    if (notification.depth == 0 && notification is ScrollEndNotification) {
      debugPrint('Stopped at ${notification.metrics.pixels}');
    }
    return false; // false = keep bubbling to Scrollbar / RefreshIndicator above
  },
  child: child,
)
```

**Return `false` from `onNotification` unless you intentionally want to swallow the event.** Returning `true` stops bubbling, which will freeze any ancestor `Scrollbar` or `RefreshIndicator` waiting on the same stream.

## The Five `ScrollNotification` Subclasses

Every `ScrollNotification` carries an immutable `ScrollMetrics` snapshot (`notification.metrics`) and the originating `BuildContext`. Switching on the concrete subtype tells you what happened:

| Notification | When it fires | Extra fields |
| --- | --- | --- |
| `ScrollStartNotification` | Activity flips from not-scrolling to scrolling | `dragDetails` (non-null if started by touch) |
| `ScrollUpdateNotification` | `pixels` changed during layout or frame tick | `scrollDelta`, `dragDetails` |
| `OverscrollNotification` | `applyBoundaryConditions` refused part of a move | `overscroll`, `velocity`, `dragDetails` |
| `ScrollEndNotification` | Activity flips back to idle / hold | `dragDetails` (non-null if ended right on finger up) |
| `UserScrollNotification` | User drag direction changes (`forward`, `reverse`, `idle`) | `direction` (`ScrollDirection`) |

> **Aside:** In `UserScrollNotification`, `ScrollDirection.reverse` means scrolling *down* toward higher `pixels` (finger moving up), while `ScrollDirection.forward` means scrolling back toward `0.0`. The enum names describe the movement of the *content* relative to its origin, which feels inverted until you remember that content moves `-pixels`.

## Nested Scroll Views and `depth`

Suppose a vertical `ListView` contains a horizontal `PageView` carousel on row 0. When the user swipes the carousel horizontally, its `ScrollPosition` dispatches `ScrollUpdateNotification`s that bubble right through your outer `NotificationListener`!

Flutter solves this with `ViewportNotificationMixin.depth`. Every viewport element mixes in `ViewportElementMixin`, which increments `notification.depth` by `1` as a notification passes out of that viewport:

- A notification from the outer `ListView` passes through **zero** enclosing viewports before reaching a listener right above the `ListView`, so `notification.depth == 0`.
- A notification from the inner `PageView` passes through the `PageView`'s own viewport *and* the outer `ListView`'s viewport, arriving with `notification.depth == 1`.

```dart
// Flutter's built-in predicate used by Scrollbar and RefreshIndicator:
bool defaultScrollNotificationPredicate(ScrollNotification notification) {
  return notification.depth == 0;
}
```

Checking `notification.depth == 0` (or `notification.metrics.axis == Axis.vertical`) keeps inner carousels from triggering outer pull-to-refresh indicators or pagination loaders.

## `ScrollMetricsNotification` When Content Resizes

What if your list sits at `pixels == 0.0`, new items stream in so `maxScrollExtent` grows from `0.0` to `800.0`, and the user hasn't touched the screen? No `ScrollUpdateNotification` fires because `pixels` didn't change — yet a "Scroll to bottom" button or custom scrollbar thumb now needs to appear.

For that exact case, `ScrollPosition.applyContentDimensions` schedules a `ScrollMetricsNotification` (via microtask after layout) whenever the metrics snapshot changes:

```dart
NotificationListener<ScrollMetricsNotification>(
  onNotification: (ScrollMetricsNotification notification) {
    final bool canScroll = notification.metrics.maxScrollExtent > 0.0;
    // Update "scroll to bottom" button visibility...
    return false;
  },
  child: child,
)
```

Notice that **`ScrollMetricsNotification` extends `Notification` directly, not `ScrollNotification`.** A `NotificationListener<ScrollNotification>` will never receive it — listen for `ScrollMetricsNotification` explicitly when you care about resize events.

## Common Pitfalls

**Calling `setState` unconditionally inside `onNotification`.** `ScrollUpdateNotification` fires at `60Hz`–`120Hz`. Calling `setState` on every notification rebuilds your entire subtree every frame; compute a boolean threshold (such as `final bool scrolled = notification.metrics.pixels > 0`) and only call `setState` when that boolean flips.

**Triggering infinite load-more loops near the bottom.** Checking `notification.metrics.extentAfter < 200` inside `ScrollUpdateNotification` will fire dozens of times while the user scrolls through the final `200` pixels. Guard your pagination call with an `_isLoading` flag and check `notification.depth == 0`.

That's `ScrollNotification` end to end: five bubbling lifecycle events plus out-of-band `ScrollMetricsNotification`, scoped cleanly across nested viewports by `depth`. Next, we'll look at `ScrollBehavior` and `ScrollConfiguration` — how Flutter decides platform physics, scrollbars,overscroll indicators, and allowed drag devices across an entire subtree.
