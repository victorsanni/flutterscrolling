---
title: Nested Scrolling
nav: Nested Scrolling
description: When you actually need NestedScrollView, how its coordinator splits one gesture across two positions, and why SliverOverlapAbsorber exists.
---

This guide walks experienced Flutter developers through `NestedScrollView` and nested scroll coordination. By the end, you'll know when a single `CustomScrollView` already solves your layout without nesting, how `_NestedScrollCoordinator` splits drags and flings between an outer header and inner tab lists, and why pinned headers inside `NestedScrollView` need `SliverOverlapAbsorber` + `SliverOverlapInjector`. We'll skip custom 2D viewports — this is about coupled outer/inner vertical scrolling, and only that.

## What This Guide Covers

- **Do You Actually Need `NestedScrollView`?** — Why 80% of "nested scroll" screens are really just one `CustomScrollView` with multiple slivers.
- **The One Case That Truly Needs It** — Collapsing outer header + horizontally swipeable `TabBarView` where each tab scrolls independently.
- **How `_NestedScrollCoordinator` Splits a Drag** — One gesture driving `_outerPosition` first and `_innerPositions` second.
- **`SliverOverlapAbsorber` and `SliverOverlapInjector`** — Forwarding outer pinned-header overlap across the viewport boundary.
- **Common Pitfalls** — Passing a custom `controller` to the inner `ListView`, forgetting `PageStorageKey` on tabs, and putting orthogonal carousels inside `NestedScrollView`.

## Do You Actually Need `NestedScrollView`?

Before reaching for `NestedScrollView`, check what you are putting inside what:

- **Horizontal `PageView` or card strip inside a vertical `ListView`?** You do *not* need `NestedScrollView`. Flutter's gesture arena automatically disambiguates perpendicular axes (`HorizontalDragGestureRecognizer` vs `VerticalDragGestureRecognizer`).
- **A banner, a grid, and two lists scrolling together vertically?** You do *not* need `NestedScrollView`. Put `SliverToBoxAdapter`, `SliverGrid`, and two `SliverList`s inside a single `CustomScrollView`.

## The One Case That Truly Needs It

Suppose a profile screen has a `240px` collapsing header + pinned `TabBar` at the top, and a swipeable `TabBarView` ("Posts", "Media", "Likes") filling the body below.

A single `CustomScrollView` cannot contain a `TabBarView` whose children are slivers — `TabBarView` is a `RenderBox` widget (`PageView`) that clips and slides whole pages horizontally, and each tab wants to remember its own vertical scroll position! That requires **two viewports**: an outer `CustomScrollView` for the collapsible header, and an inner `ScrollView` inside each tab.

{{figure:nested-scroll|NestedScrollView's coordinator routes upward drags to collapse the outer header first, then scrolls the active inner tab list.}}

## How `_NestedScrollCoordinator` Splits a Drag

If you simply placed a `ListView` inside the body of a normal `ScrollView`, the inner `ListView` would win the vertical drag arena and scroll while the outer header sat frozen at the top.

`NestedScrollView` solves this with a private `_NestedScrollCoordinator` that intercepts `Scrollable` input and owns custom `_NestedScrollPosition` instances for both the outer header and every mounted inner tab:

1. **Scrolling down (`delta < 0`, finger moving up):** The coordinator feeds the delta to `_outerPosition` *first* until `_outerPosition` reaches its `maxScrollExtent` (the header is fully collapsed), then feeds every remaining pixel of that same drag frame to the active inner position!
2. **Scrolling up (`delta > 0`, finger moving down):** Under `floatHeaderSlivers: false` (default), the coordinator scrolls the inner list all the way back to `0.0` *first*, and only then expands the outer header. With `floatHeaderSlivers: true`, reversing direction immediately pulls the floating outer header back into view first.
3. **Liftoff flings:** One ballistic simulation is split across both positions so flicking upward collapses the header and seamlessly continues coasting down the inner `ListView`.

For the inner `ListView` to register with `_NestedScrollCoordinator`, **the inner `ListView` must inherit `NestedScrollView`'s `PrimaryScrollController` — do not pass your own `ScrollController` to the inner `ListView`!**

## `SliverOverlapAbsorber` and `SliverOverlapInjector`

When an outer `SliverAppBar(pinned: true)` stays pinned at the top of `NestedScrollView`, its `SliverGeometry` reports `overlap` inside the *outer* viewport. The *inner* `CustomScrollView` lives inside a separate viewport in `body`, so it has no idea the top `104px` of its space is covered by the pinned outer app bar and `TabBar`! Without help, row `0` of each tab renders hidden behind the pinned bar.

`SliverOverlapAbsorber` and `SliverOverlapInjector` bridge that gap across the two viewports:

```dart
NestedScrollView(
  headerSliverBuilder: (BuildContext context, bool innerBoxIsScrolled) {
    return <Widget>[
      SliverOverlapAbsorber(
        handle: NestedScrollView.sliverOverlapAbsorberHandleFor(context),
        sliver: SliverAppBar(
          title: const Text('Profile'),
          pinned: true,
          forceElevated: innerBoxIsScrolled,
          bottom: TabBar(controller: tabController, tabs: tabs),
        ),
      ),
    ];
  },
  body: TabBarView(
    controller: tabController,
    children: <Widget>[
      for (final String tab in tabNames)
        Builder(
          builder: (BuildContext context) {
            return CustomScrollView(
              key: PageStorageKey<String>(tab),
              slivers: <Widget>[
                SliverOverlapInjector(
                  handle: NestedScrollView.sliverOverlapAbsorberHandleFor(context),
                ),
                SliverList.builder(
                  itemCount: 30,
                  itemBuilder: (BuildContext context, int i) => ListTile(title: Text('$tab #$i')),
                ),
              ],
            );
          },
        ),
    ],
  ),
)
```

`SliverOverlapAbsorber` swallows the pinned header's `overlap` in the outer viewport and writes its pixel height into a shared `SliverOverlapAbsorberHandle`; `SliverOverlapInjector` sits first inside each inner `CustomScrollView` and expands by that exact pixel height so row `0` starts right below the `TabBar`.

## Common Pitfalls

**Passing a `ScrollController` to an inner `ListView` inside `NestedScrollView.body`.** Passing `ListView(controller: myController)` disconnects that list from the `PrimaryScrollController` supplied by `NestedScrollView`, breaking coordinator handoff completely. Control the outer view via `NestedScrollView(controller: ...)` or read `NestedScrollViewState.innerController` via a `GlobalKey<NestedScrollViewState>`.

**Calling `NestedScrollView.sliverOverlapAbsorberHandleFor(context)` with the wrong `context`.** Inside `body`, you must look up the handle using a `Builder` *under* `NestedScrollView` (not the outer `build` method's `context` above `NestedScrollView`), or Flutter won't find the ancestor `_InheritedNestedScrollView`.

That's `NestedScrollView` end to end: reach for a single `CustomScrollView` whenever possible, and when a `TabBarView` truly forces two vertical viewports, let `_NestedScrollCoordinator` drive the inner views via `PrimaryScrollController` while `SliverOverlapAbsorber` + `SliverOverlapInjector` keep pinned headers aligned. Our final guide covers scrolling along *both* axes simultaneously: `TwoDimensionalScrollView`.
