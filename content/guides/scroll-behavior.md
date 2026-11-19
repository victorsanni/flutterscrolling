---
title: Scroll Behavior
nav: Scroll Behavior
description: How ScrollConfiguration and ScrollBehavior supply default physics, scrollbars, overscroll indicators, and drag devices.
---

This guide walks experienced Flutter developers through `ScrollBehavior` and `ScrollConfiguration`. By the end, you'll understand where default iOS bounce vs Android stretch comes from, why desktop mouse dragging is disabled by default (and how to enable it in three lines), and how to swap scrollbars or overscroll effects across one screen or your whole app. We'll skip custom `ScrollPhysics` math and sliver layout — this is about ambient scrolling policy, and only ambient policy.

## What This Guide Covers

- **`ScrollBehavior` vs `ScrollConfiguration`** — The policy object and the `InheritedWidget` that distributes it.
- **The Four Things `ScrollBehavior` Controls** — Default physics, scrollbars, overscroll indicators, and `dragDevices`.
- **`copyWith` vs Subclassing** — Changing behavior for one subtree without writing a new class.
- **Enabling Mouse and Trackpad Dragging** — Why `PointerDeviceKind.mouse` is excluded by default and how to opt in.
- **Common Pitfalls** — Overwriting `MaterialScrollBehavior` accidentally and stacking duplicate `Scrollbar`s.

## `ScrollBehavior` vs `ScrollConfiguration`

Whenever a `Scrollable` builds without an explicit `physics:` argument, where does it get `BouncingScrollPhysics` on iOS and `ClampingScrollPhysics` on Android?

It reads `ScrollConfiguration.of(context)`, an `InheritedWidget` that holds a `ScrollBehavior` instance:

- `MaterialApp` installs `MaterialScrollBehavior` at the root of your app (unless you pass `MaterialApp(scrollBehavior: ...)`).
- `CupertinoApp` installs `CupertinoScrollBehavior`.
- Bare `WidgetsApp` (or tests using `Directionality` alone) falls back to the base `ScrollBehavior`.

## The Four Things `ScrollBehavior` Controls

During `ScrollableState.build` and `_updatePosition`, `Scrollable` asks the ambient `ScrollBehavior` four questions:

1. **`getScrollPhysics(BuildContext context)`** — Returns the ambient `ScrollPhysics` chain. On `iOS` and `macOS`, base `ScrollBehavior` returns `BouncingScrollPhysics(parent: RangeMaintainingScrollPhysics())`; on `android`, `fuchsia`, `linux`, and `windows`, it returns `ClampingScrollPhysics(parent: RangeMaintainingScrollPhysics())`.
2. **`buildScrollbar(context, child, details)`** — Wraps the viewport in a platform scrollbar on desktop platforms (`macOS`, `linux`, `windows`). `MaterialScrollBehavior` wraps with `Scrollbar`; `CupertinoScrollBehavior` wraps with `CupertinoScrollbar`. On mobile touch platforms, it returns `child` untouched unless you add a `Scrollbar` widget yourself.
3. **`buildOverscrollIndicator(context, child, details)`** — Wraps the viewport in an edge effect when clamping physics refuse movement. `MaterialScrollBehavior` wraps Android views in `StretchingOverscrollIndicator` (under Material 3) or `GlowingOverscrollIndicator` (Material 2); iOS needs none because `BouncingScrollPhysics` moves the content itself.
4. **`dragDevices`** — Returns the `Set<PointerDeviceKind>` allowed to start drag gestures (`touch`, `stylus`, `invertedStylus`, `trackpad`, and `unknown` by default — **not** `mouse`).

## `copyWith` vs Subclassing

For local tweaks — removing scrollbars around a custom carousel, turning off the Android stretch effect on one screen, or changing physics for a subtree — call `ScrollConfiguration.of(context).copyWith(...)` instead of writing a subclass:

```dart
ScrollConfiguration(
  behavior: ScrollConfiguration.of(context).copyWith(
    scrollbars: false,
    overscroll: false,
  ),
  child: CustomCarousel(),
)
```

For app-wide policy, pass a custom `ScrollBehavior` to `MaterialApp.scrollBehavior`:

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

**Extend or `copyWith` `MaterialScrollBehavior` (not base `ScrollBehavior`) inside a Material app.** Extending raw `ScrollBehavior` drops Material's desktop `Scrollbar` and Android's `StretchingOverscrollIndicator`, reverting Android edges to an old cyan glow or nothing at all.

## Enabling Mouse and Trackpad Dragging

On web and desktop, Flutter intentionally excludes `PointerDeviceKind.mouse` from `ScrollBehavior.dragDevices`: users expect clicking and dragging with a mouse to select text or drag items, while scrolling happens via mouse wheel, trackpad two-finger pan (`PointerDeviceKind.trackpad`), or dragging the scrollbar thumb.

For horizontal card carousels or canvas-like surfaces where mouse click-drag *should* scroll, add `PointerDeviceKind.mouse` via `copyWith`:

```dart
ScrollConfiguration(
  behavior: ScrollConfiguration.of(context).copyWith(
    dragDevices: <PointerDeviceKind>{
      PointerDeviceKind.touch,
      PointerDeviceKind.mouse,
      PointerDeviceKind.trackpad,
    },
  ),
  child: PageView(children: pages),
)
```

## Common Pitfalls

**Wrapping a desktop `ListView` in `Scrollbar` without a shared `ScrollController`.** On macOS, Windows, and Linux, `MaterialScrollBehavior` *already* wraps every vertical scroll view in an automatic `Scrollbar`. Adding a manual `Scrollbar(child: ListView(...))` on desktop draws two scrollbars — or triggers a `Scrollbar` position assertion unless you either pass the same `controller` to both or set `scrollbars: false` on `ScrollConfiguration`.

**Passing `physics:` on a `ListView` expecting it to replace `ScrollBehavior` completely.** Remember from [Scroll Physics](/guides/scroll-physics) that widget physics *prepend* onto `ScrollBehavior.getScrollPhysics(context)` via `applyTo`. If you pass `AlwaysScrollableScrollPhysics()` on a `ListView`, its parent link is still the ambient `BouncingScrollPhysics` or `ClampingScrollPhysics` from `ScrollBehavior`.

That finishes the widget-and-position half of Flutter scrolling. Next, we cross into the rendering half — starting with `Viewport` and how a single-child scroll view differs fundamentally from a sliver viewport.
