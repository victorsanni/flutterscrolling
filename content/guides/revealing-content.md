---
title: Revealing Content
nav: Revealing Content
description: How Scrollable.ensureVisible, getOffsetToReveal, and showOnScreen scroll a target into view — and why unmounted lazy items can't be found by BuildContext.
---

This guide walks experienced Flutter developers through Flutter's reveal pipeline: `Scrollable.ensureVisible`, `RenderAbstractViewport.getOffsetToReveal`, and `RenderObject.showOnScreen`. By the end, you'll understand how Flutter computes the exact scroll offset needed to bring any mounted widget into view, how `alignment` and `alignmentPolicy` differ, and why `ensureVisible` cannot jump to an unbuilt item in a lazy `ListView.builder`. We'll skip custom physics simulations — this is about finding and scrolling to a target widget, and only that.

## What This Guide Covers

- **Two Entry Points: `ensureVisible` and `showOnScreen`** — Widget-level reveal vs render-tree auto-scroll (used by focused `TextField`s).
- **How `getOffsetToReveal` Computes the Target Offset** — Walking from target `RenderObject` up to `RenderAbstractViewport`.
- **`alignment` vs `alignmentPolicy`** — Pinning to a specific fraction of the viewport vs scrolling only the minimum distance required.
- **Why Lazy Lists Can't Reveal Unmounted Items** — What happens when item `400` has no `BuildContext` yet, and the three clean alternatives.
- **Common Pitfalls** — Hidden behind a custom overlay, soft keyboard race conditions, and calling `ensureVisible` on an unmounted `GlobalKey`.

## Two Entry Points: `ensureVisible` and `showOnScreen`

Flutter has two closely related ways to scroll a descendant into view:

1. **`Scrollable.ensureVisible(context, ...)`** is the explicit widget API you call from app code. Starting at `context`, it walks *every* enclosing `Scrollable` (both inner horizontal carousels and outer vertical lists!) and calls `position.ensureVisible(...)` on each one, returning a `Future<void>` when all animations complete.
2. **`RenderObject.showOnScreen(...)`** is the low-level render tree walk triggered automatically when a `TextField` gains focus or an accessibility screen reader moves focus to an off-screen node. Each parent render object translates the target `Rect` into its own coordinate space until `RenderViewportBase.showInViewport` adjusts `offset`.

```dart
await Scrollable.ensureVisible(
  targetKey.currentContext!,
  alignment: 0.5, // 0.0 = leading edge, 0.5 = centered, 1.0 = trailing edge
  duration: const Duration(milliseconds: 250),
  curve: Curves.easeOutCubic,
);
```

## How `getOffsetToReveal` Computes the Target Offset

When `ScrollPosition.ensureVisible` runs on a target `RenderObject`, how does it know which `pixels` value puts that object on screen?

It looks up `RenderAbstractViewport.of(object)` and calls `viewport.getOffsetToReveal(object, alignment)`:

1. `RenderViewport` walks up from `object` to the direct child `RenderSliver` that contains it, accumulating the box's paint offset inside that sliver.
2. It adds the sliver's layout position relative to the scroll origin (`precedingScrollExtent` in forward slivers).
3. If earlier pinned headers reported `geometry.maxScrollObstructionExtent` (for example, a `56px` `PinnedHeaderSliver`), `getOffsetToReveal` subtracts that obstructed band from the usable viewport height so `alignment: 0.0` lands cleanly *below* the pinned header instead of tucked behind it!

## `alignment` vs `alignmentPolicy`

By default, `ScrollPositionAlignmentPolicy.explicit` always moves the scroll view so the target sits at `alignment` (`0.0` = flush with the top/left edge, `0.5` = dead center, `1.0` = flush with the bottom/right edge) — **even if the widget was already completely visible on screen.**

For keyboard arrow navigation or form validation, jumping an already-visible field to the top edge feels jarring. Pass one of the two minimal-movement policies instead:

- **`ScrollPositionAlignmentPolicy.keepVisibleAtEnd`** — If the target is below the bottom edge, scrolls just enough to reveal it at the trailing edge (`1.0`); if already fully visible, **does nothing**.
- **`ScrollPositionAlignmentPolicy.keepVisibleAtStart`** — If the target is above the top edge, scrolls just enough to reveal it at the leading edge (`0.0`); if already fully visible, **does nothing**.

```dart
// Scrolls down only if the focused item is cut off at the bottom; otherwise stays put:
await Scrollable.ensureVisible(
  itemContext,
  alignmentPolicy: ScrollPositionAlignmentPolicy.keepVisibleAtEnd,
  duration: const Duration(milliseconds: 180),
);
```

## Why Lazy Lists Can't Reveal Unmounted Items

Here is the fundamental limitation of `Scrollable.ensureVisible`: **it requires a live `BuildContext` (and mounted `RenderObject`) for the target.**

In a `ListView.builder` with `1,000` items where rows `0..12` are on screen, row `500` has not been built yet — `itemKeys[500].currentContext` is `null`! You have three clean ways to jump to index `500` depending on your layout:

1. **Uniform or predictable heights:** Set `itemExtent`, `prototypeItem`, or `itemExtentBuilder` on your `ListView` and compute the exact offset directly (`controller.animateTo(500 * itemExtent, ...)`).
2. **Bounded item count (`< 100` items):** Use `SingleChildScrollView` + `Column` if every item is lightweight and already mounted anyway.
3. **Arbitrary variable-height thousands-item lists (chat jump-to-message):** Anchor `CustomScrollView(center: targetSliverKey)` around the jumped-to slice, or use an indexed list package (`scrollable_positioned_list` / `super_sliver_list`) that maintains an index-to-sliver-offset map.

## Common Pitfalls

**Calling `ensureVisible` right when a `TextField` gains focus before the keyboard finishes animating.** While the soft keyboard slides up over ~250ms, `MediaQuery.viewInsets.bottom` grows frame by frame. `EditableText` already schedules `showOnScreen` automatically via `WidgetsBindingObserver.didChangeMetrics`; if you call a manual `ensureVisible` in `onTap`, it runs *before* the viewport shrinks for the keyboard and stops too high. Set `Scaffold.resizeToAvoidBottomInset: true` and `TextField.scrollPadding` instead.

**Floating overlays (`Stack` headers) hiding revealed items.** `getOffsetToReveal` only knows about obstructions inside the `Viewport` (`PinnedHeaderSliver`, `SliverAppBar`). If you float a translucent bar *outside* the `CustomScrollView` inside a `Stack`, `ensureVisible(alignment: 0.0)` will place your item right underneath that `Stack` overlay. Either move the bar into a sliver (`PinnedHeaderSliver`) or pad the scroll view with `SliverPadding(padding: EdgeInsets.only(top: barHeight))`.

That's content reveal end to end: `Scrollable.ensureVisible` walks ancestor scrollables, `getOffsetToReveal` translates target render bounds into a `pixels` offset while respecting sliver obstructions, and `itemExtent` arithmetic handles unmounted lazy indices. Next, we'll look at `NestedScrollView` — how one drag smoothly collapses an outer header and then scrolls an inner `TabBarView` list.
