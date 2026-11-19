---
title: NotificationListener<ScrollNotification>
nav: onNotification
description: Handle bubbling ScrollNotifications and ScrollMetricsNotifications from any descendant scrollable.
---

`NotificationListener<T>` intercepts scroll notifications bubbling up the element tree via its `bool Function(T notification)? onNotification` callback.

- Return `false` to allow the notification to keep bubbling to ancestors (`Scrollbar`, `RefreshIndicator`, `Scaffold`).
- Return `true` to stop bubbling at this listener.

## Default Filter (`defaultScrollNotificationPredicate`)

Any nested scroll view (like a horizontal carousel inside a vertical list) bubbles through outer listeners with `notification.depth > 0`. Filter to the nearest child viewport with `notification.depth == 0`:

```dart
NotificationListener<ScrollNotification>(
  onNotification: (ScrollNotification notification) {
    if (notification.depth != 0) {
      return false;
    }
    // Handle direct child scroll view here.
    return false;
  },
  child: child,
)
```

## Show App-Bar Divider Only When Scrolled Under

Example that toggles `setState` *only* when the boolean `isElevated` actually flips, avoiding `60fps` widget rebuilds.

```dart
bool _isElevated = false;

Widget buildBody(Widget scrollView) {
  return NotificationListener<ScrollUpdateNotification>(
    onNotification: (ScrollUpdateNotification notification) {
      if (notification.depth == 0) {
        final bool next = notification.metrics.extentBefore > 0.0;
        if (next != _isElevated) {
          setState(() => _isElevated = next);
        }
      }
      return false;
    },
    child: scrollView,
  );
}
```

## Hide Floating Action Button on Downward Drag

Example that listens specifically to `UserScrollNotification` so programmatic animations or bounce-back springs do not hide the button unexpectedly.

```dart
NotificationListener<UserScrollNotification>(
  onNotification: (UserScrollNotification notification) {
    if (notification.depth != 0) {
      return false;
    }
    if (notification.direction == ScrollDirection.reverse && _fabVisible) {
      setState(() => _fabVisible = false);
    } else if (notification.direction == ScrollDirection.forward && !_fabVisible) {
      setState(() => _fabVisible = true);
    }
    return false;
  },
  child: listView,
)
```

## React When Content Grows Without Scrolling (`ScrollMetricsNotification`)

Example that catches post-layout extent changes (`ScrollMetricsNotification` does not extend `ScrollNotification`).

```dart
NotificationListener<ScrollMetricsNotification>(
  onNotification: (ScrollMetricsNotification notification) {
    if (notification.depth == 0) {
      final bool scrollable = notification.metrics.maxScrollExtent > 0.0;
      if (scrollable != _canScrollDown) {
        setState(() => _canScrollDown = scrollable);
      }
    }
    return false;
  },
  child: listView,
)
```
