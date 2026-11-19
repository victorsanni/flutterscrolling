---
title: Lazy Children
nav: Lazy Children
description: How SliverList and SliverGrid build widgets mid-layout, manage the cacheExtent window, and honor AutomaticKeepAlive.
---

This guide walks experienced Flutter developers through lazy child virtualization in `SliverList`, `SliverGrid`, `SliverChildDelegate`, and `RenderSliverMultiBoxAdaptor`. By the end, you'll understand how a render object triggers widget builds *during* `performLayout`, how `cacheExtent` decides when off-screen items mount and unmount, why `itemExtent` / `prototypeItem` transform jump performance, and how `AutomaticKeepAliveClientMixin` parks elements off-screen without destroying their `State`. We'll skip custom 2D viewports and sticky headers — this is about 1D lazy child management, and only that.

## What This Guide Covers

- **Three Cooperating Layers** — How `SliverChildDelegate`, `SliverMultiBoxAdaptorElement`, and `RenderSliverMultiBoxAdaptor` divide lazy building.
- **Building Widgets Mid-Layout** — How `invokeLayoutCallback` lets `RenderSliverList` ask its `Element` for item `index + 1` on the fly.
- **`cacheExtent` and Garbage Collection** — When leading and trailing children are built and when `collectGarbage` unmounts them.
- **Why `itemExtent` and `prototypeItem` Matter** — Avoiding $O(N)$ layout walks on long `jumpTo` / scrollbar drags.
- **Keeping Off-Screen State Alive** — How `AutomaticKeepAliveClientMixin` moves unmounted items into `_keepAliveBucket`.
- **Common Pitfalls** — `addAutomaticKeepAlives` memory leaks, missing keys on mutable lists, and expensive `itemBuilder` work.

## Three Cooperating Layers

Normally Flutter builds widgets *first* (`build` phase) and lays out render objects *second* (`layout` phase). A lazy `ListView.builder` with `10,000` variable-height items cannot work in that order: during `build`, nobody knows whether `3` items or `14` items will fit inside a `600px` viewport!

Flutter solves this by splitting `SliverList` across three objects:

1. **`SliverChildDelegate`** (`SliverChildBuilderDelegate` or `SliverChildListDelegate`) — Knows how to turn an `int index` into a `Widget?` (returning `null` past the end).
2. **`SliverMultiBoxAdaptorElement`** (`implements RenderSliverBoxChildManager`) — Holds a `SplayTreeMap<int, Element>` of currently mounted item elements and builds or unmounts them on demand.
3. **`RenderSliverMultiBoxAdaptor`** (base class of `RenderSliverList`, `RenderSliverFixedExtentList`, and `RenderSliverGrid`) — Maintains a doubly linked list of active `RenderBox` children and walks forward/backward until the visible + cache window is covered.

## Building Widgets Mid-Layout

Inside `RenderSliverList.performLayout`, each step forward measures the current child's bottom edge. If space remains inside `scrollOffset + remainingCacheExtent`, the render object asks its `childManager` (the `Element`) to materialize `index + 1` right then and there via `invokeLayoutCallback`:

```dart
// Inside RenderSliverMultiBoxAdaptor._createOrObtainChild:
invokeLayoutCallback<SliverConstraints>((SliverConstraints constraints) {
  // Runs a scoped Element build pass safely inside performLayout:
  childManager.createChild(index, after: currentChild);
});
```

**Because `itemBuilder` runs *inside* the sliver's layout pass, an `itemBuilder` cannot mutate widget state above the viewport.** Calling `setState` on an ancestor while `itemBuilder` executes will throw `"setState() or markNeedsBuild() called during build/layout"`.

## `cacheExtent` and Garbage Collection

If `RenderSliverList` only kept strictly visible items alive, scrolling `1px` would constantly build a row at one edge while destroying one at the other, and images one pixel off-screen wouldn't start decoding until already in view.

`Viewport` extends the active window in both directions by a cache margin (`250.0` logical pixels by default, configurable via `scrollCacheExtent: ScrollCacheExtent.pixels(...)` or `.viewport(...)`):

{{figure:cache-extent|RenderSliverList keeps items mounted across the visible viewport plus leading and trailing cache regions, and unmounts everything outside.}}

At the end of `performLayout`, `RenderSliverList` counts how many mounted children now lie completely before `cacheOrigin` (`leadingGarbage`) and completely after the trailing cache edge (`trailingGarbage`), and calls:

```dart
collectGarbage(leadingGarbage, trailingGarbage);
```

`collectGarbage` tells `SliverMultiBoxAdaptorElement` to unmount those off-cache `Element`s (disposing their `State` and `RenderBox`), keeping memory proportional to screen height rather than list length.

## Why `itemExtent` and `prototypeItem` Matter

In a plain `ListView.builder`, `RenderSliverList` has no idea how tall item `5,000` is without building and laying out items `0..4,999` or estimating from the few items currently mounted. Dragging a scrollbar thumb straight from top to bottom forces rough extent estimates — and `scrollOffsetCorrection` retries when scrolling back up.

Whenever your items share uniform or predictable heights, tell Flutter up front:

- **`itemExtent: 56.0`** switches from `RenderSliverList` to `RenderSliverFixedExtentList`. Item `i` is known to live at `[i * 56.0, (i + 1) * 56.0]` in $O(1)$ arithmetic — jumping to item `50,000` builds *only* the ~15 rows around index `50,000`.
- **`prototypeItem: const MyRowPlaceholder()`** lays out one invisible prototype widget once to measure its height cleanly across dynamic font sizes, then uses that exact height with `O(1)` fixed-extent math.
- **`itemExtentBuilder: (index, dimensions) => ...`** gives $O(1)$ lookup when item heights vary by index (for example, section headers of `40px` and rows of `72px`) without building off-screen widgets.

## Keeping Off-Screen State Alive

By default, `SliverChildBuilderDelegate` wraps every item in `AutomaticKeepAlive` (`addAutomaticKeepAlives: true`). An item's `State` can opt out of destruction when scrolled past `cacheExtent` by mixing in `AutomaticKeepAliveClientMixin`:

```dart
class _CommentDraftState extends State<CommentDraft>
    with AutomaticKeepAliveClientMixin {
  final TextEditingController _text = TextEditingController();

  @override
  bool get wantKeepAlive => _text.text.isNotEmpty;

  @override
  Widget build(BuildContext context) {
    super.build(context); // required: sends KeepAliveNotification when wantKeepAlive changes
    return TextField(controller: _text, onChanged: (_) => updateKeepAlive());
  }
}
```

When `collectGarbage` tries to evict a child whose `SliverMultiBoxAdaptorParentData.keepAlive` is `true`, **it detaches the child from the active paint/layout linked list and parks it in `_keepAliveBucket` instead of unmounting its `Element`.** Its `State` (and `TextEditingController` cursor!) stays intact in memory at zero per-frame layout/paint cost, and re-attaches instantly if scrolled back into view.

## Common Pitfalls

**Returning `wantKeepAlive => true` unconditionally on hundreds of heavy items.** Every kept-alive item retains its full `Element`, `State`, `RenderBox` subtree, and decoded image references in `_keepAliveBucket`. Tie `wantKeepAlive` to an actual condition (such as unsaved input) and call `updateKeepAlive()` once it clears.

**Reordering or deleting items in `ListView.builder` without `Key`s (or `findChildIndexCallback`).** `SliverMultiBoxAdaptorElement` keys active children by integer index unless told otherwise. If you delete index `0` from a stateful list without keys, old index `0`'s `State` stays mounted and receives new index `0`'s widget data. Pass a stable `ValueKey` on each item (and `findChildIndexCallback` if using kept-alive items so Flutter can relocate parked elements to their new index).

That's lazy child virtualization end to end: `RenderSliverMultiBoxAdaptor` builds children mid-layout across the visible + `cacheExtent` window, `collectGarbage` unmounts or buckets off-cache items, and `itemExtent` / `prototypeItem` turn layout math into $O(1)$ index arithmetic. Next, we'll look at headers that refuse to scroll off-screen: `PinnedHeaderSliver`, `SliverResizingHeader`, `SliverFloatingHeader`, and `SliverPersistentHeader`.
