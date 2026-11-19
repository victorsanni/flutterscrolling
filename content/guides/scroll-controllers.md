---
title: Scroll Controllers
nav: Scroll Controllers
description: How ScrollController creates, observes, and commands a ScrollPosition — and what PrimaryScrollController does when you omit one.
---

This guide walks experienced Flutter developers through `ScrollController`, `PageController`, and `PrimaryScrollController`. By the end, you'll understand what a controller actually owns, how `attach` and `detach` work when widgets rebuild, and when Flutter automatically shares an inherited `PrimaryScrollController`. We'll skip `ScrollNotification` bubbling and sliver internals — this is about the handle you hold in widget state, and only that handle.

## What This Guide Covers

- **A Remote Control, Not the Position** — Why `ScrollController` delegates almost everything to its attached `ScrollPosition`s.
- **Lifecycle: `createScrollPosition`, `attach`, and `detach`** — What happens when a `Scrollable` mounts, updates, and unmounts.
- **Reading and Moving the Offset** — `offset`, `hasClients`, `jumpTo`, `animateTo`, and listening for changes.
- **How `PrimaryScrollController` Works** — Platform-specific auto-inheritance, status-bar tap-to-top on iOS, and avoiding multi-attachment crashes.
- **Page Storage and `keepScrollOffset`** — How scroll offsets survive tab switches and route pops.
- **Common Pitfalls** — Sharing one controller across two `ListView`s, forgetting `dispose`, and reading `offset` when unattached.

## A Remote Control, Not the Position

`ScrollController` does not store `pixels` itself — it holds a list of zero or more attached `ScrollPosition` objects (`positions`) and forwards your reads and commands to them.

Even when you omit `controller:` on a `ListView`, there is still a `ScrollController` at work: `ScrollableState` creates a private fallback `ScrollController` internally so every `Scrollable` follows the exact same code path.

```dart
class _FeedState extends State<Feed> {
  final ScrollController _controller = ScrollController(
    initialScrollOffset: 120.0,
  );

  @override
  void dispose() {
    _controller.dispose(); // always dispose controllers you construct
    super.dispose();
  }
}
```

## Lifecycle: `createScrollPosition`, `attach`, and `detach`

When `ScrollableState` mounts (or swaps controllers in `didUpdateWidget`), it runs a three-step handshake with the effective `ScrollController`:

1. Calls `controller.createScrollPosition(physics, context, oldPosition)` to build the `ScrollPosition` (passing the previous `ScrollPosition` during rebuilds so the current `pixels` value carries over).
2. Calls `controller.attach(position)`, which adds `position` to `controller.positions` and subscribes `notifyListeners` to the position.
3. On unmount or controller swap, calls `controller.detach(position)` before disposing the position.

Subclasses of `ScrollController` exist primarily to customize step 1. `PageController`, for example, overrides `createScrollPosition` to return a `_PagePosition` that speaks in `page` indices alongside raw `pixels`.

## Reading and Moving the Offset

Once a `Scrollable` is mounted, `controller.hasClients` becomes `true`:

```dart
if (_controller.hasClients) {
  final double current = _controller.offset; // shorthand for position.pixels
  await _controller.animateTo(
    0.0,
    duration: const Duration(milliseconds: 300),
    curve: Curves.easeOutCubic,
  );
}
```

**`controller.position` and `controller.offset` assert that *exactly one* `ScrollPosition` is attached.** If zero scrollables are attached — or if two `ListView`s accidentally share the same controller — reading `.position` or `.offset` throws immediately. By contrast, `jumpTo` and `animateTo` loop over every entry in ` List.of(_positions)`, broadcasting the move to all attached positions.

When you subscribe with `controller.addListener(...)`, your callback fires whenever `pixels` changes — **not** when `maxScrollExtent` changes without moving `pixels`. If you need to react to content-size changes too, listen for `ScrollMetricsNotification` instead (covered in [Scroll Notifications](/guides/scroll-notifications)).

## How `PrimaryScrollController` Works

`PrimaryScrollController` is an `InheritedWidget` placed near the top of `Scaffold` / `CupertinoPageScaffold` so ancestor chrome can find the screen's main vertical scroll view without manual plumbing. On iOS, tapping the system status bar animates the `PrimaryScrollController` back to `0.0`; on desktop, keyboard shortcuts (`Page Up`, `Page Down`, `Space`) can target the primary scrollable.

A `ScrollView` (`ListView`, `GridView`, `CustomScrollView`) automatically adopts `PrimaryScrollController.maybeOf(context)` only when **all** of these hold:

- You left both `controller: null` and `primary: null` (or explicitly passed `primary: true`).
- `scrollDirection` is `Axis.vertical`.
- `PrimaryScrollController.shouldInherit(context, scrollDirection)` returns `true` — which by default only happens on mobile platforms (`TargetPlatform.iOS`, `android`, `fuchsia`).

Once a `ScrollView` claims the primary controller, it wraps its subtree in `PrimaryScrollController.none` so nested vertical lists inside it don't collide on the same controller.

## Page Storage and `keepScrollOffset`

By default, `ScrollController.keepScrollOffset` is `true`. Whenever an activity settles (and during scroll updates), `ScrollPosition` writes `pixels` into the nearest `PageStorage` bucket keyed by the `Scrollable`'s `PageStorageKey`.

```dart
ListView.builder(
  key: const PageStorageKey<String>('home-feed'),
  itemCount: items.length,
  itemBuilder: itemBuilder,
)
```

Giving two tabs distinct `PageStorageKey`s lets `TabBarView` unmount an off-screen tab and restore its exact scroll offset when the user swipes back — even without keeping a `ScrollController` alive in parent state.

## Common Pitfalls

**Two sibling `ListView`s accidentally sharing `PrimaryScrollController`.** If you put two vertical `ListView`s side by side on iOS (for example in a tablet split-view) with neither `controller:` nor `primary: false`, both try to attach to the scaffold's single `PrimaryScrollController`, throwing `"ScrollController attached to multiple scroll views"`. Pass `primary: false` (or explicit controllers) to secondary lists.

**Forgetting `dispose()` on a `ScrollController`.** A `ScrollController` is a `ChangeNotifier`. Leaving it undisposed leaks listener closures and triggers memory-leak tracker failures in `flutter_test`.

**Calling `jumpTo` before `hasClients` is true.** If a `ListView` sits behind a loading spinner and hasn't mounted yet, `_controller.jumpTo(0)` does nothing (its `_positions` list is empty), while `_controller.offset` throws. Always guard with `if (_controller.hasClients)`.

That's `ScrollController` end to end: a lightweight handle that creates, attaches to, and drives `ScrollPosition`s while `PrimaryScrollController` wires the main vertical list to platform chrome. Next, we'll look at how scrolling events travel *up* the widget tree via `ScrollNotification`.
