---
title: Viewports
nav: Viewports
description: What a viewport actually does, why SingleChildScrollView only repaints while Viewport relayouts, and what shrinkWrap costs.
---

This guide walks experienced Flutter developers through Flutter's viewport render objects: `_RenderSingleChildViewport`, `RenderViewport`, and `RenderShrinkWrappingViewport`. By the end, you'll understand why `SingleChildScrollView` and `CustomScrollView` take completely different approaches to scrolling, how `RenderViewport` lays out slivers from an anchor or `center` key, and why `shrinkWrap: true` changes layout complexity from $O(\text{visible})$ to $O(\text{all items})$. We'll skip individual `SliverGeometry` fields until the next guide — this is about the window itself, and only the window.

## What This Guide Covers

- **The Viewport's Three Jobs** — Sizing the window, reporting extents to `ViewportOffset`, and painting clipped content.
- **Box Viewport vs Sliver Viewport** — Why `SingleChildScrollView` calls `markNeedsPaint` on scroll while `RenderViewport` calls `markNeedsLayout`.
- **Layout Retries and Offset Corrections** — How `RenderViewport.performLayout` handles slivers whose estimated scroll extents shift mid-scroll.
- **`center` and `anchor`** — Growing scroll content in both directions from a middle item (like a chat timeline).
- **What `shrinkWrap: true` Really Does** — Replacing `Viewport` with `ShrinkWrappingViewport` and what it costs.
- **Common Pitfalls** — Tall columns inside `SingleChildScrollView`, unbounded viewport constraints, and nested `shrinkWrap` lists.

## The Viewport's Three Jobs

No matter how simple or sophisticated a viewport is, its contract with the rest of Flutter comes down to three responsibilities:

1. **Choose a `RenderBox` size** inside the incoming `BoxConstraints` from its parent widget, and pass the main-axis length to `offset.applyViewportDimension(...)`.
2. **Measure scrollable bounds** (`minScrollExtent` and `maxScrollExtent`) and pass them to `offset.applyContentDimensions(...)`.
3. **Paint visible children** shifted by `-offset.pixels` inside a clip rectangle (when `clipBehavior != Clip.none`), applying the same shift to hit-testing and coordinate transforms.

You can see all three jobs in roughly 100 lines of plain `RenderBox` code in the [Minimal Viewport](/examples/minimal-viewport) example.

## Box Viewport vs Sliver Viewport

Flutter ships two fundamentally different viewport architectures, and choosing the wrong one is behind most scrolling performance bugs:

| | `SingleChildScrollView` | `Viewport` (`ListView` / `CustomScrollView`) |
| --- | --- | --- |
| Child protocol | One `RenderBox` | Zero or more `RenderSliver`s |
| Child constraints | Unbounded (`double.infinity`) along scroll axis | `SliverConstraints` with `scrollOffset` & `remainingPaintExtent` |
| Listener on `ViewportOffset` | `markNeedsPaint` | `markNeedsLayout` |
| Off-screen widgets | Built, laid out, and kept in memory all at once | Built and laid out lazily only inside visible + cache window |

Look at row 3: **`SingleChildScrollView` lays out its entire child once up front, then only repaints on scroll; `RenderViewport` runs sliver layout on every scroll frame.**

Running layout on every scroll frame sounds expensive until you realize *only* the slivers overlapping the viewport (plus `cacheExtent`) lay out any box children. Scrolling a `10,000`-row `ListView.builder` touches ~15 rows per frame; putting those `10,000` rows in a `SingleChildScrollView(child: Column(...))` builds and lays out all `10,000` on frame 1.

## Layout Retries and Offset Corrections

When you scroll backward through a variable-height `ListView.builder`, an item re-entering the top of the viewport might turn out to be `140px` tall when the list previously assumed it started `80px` earlier. If the viewport didn't adjust `pixels`, visible items on screen would suddenly jump downward by `60px`.

`RenderViewport.performLayout` handles this with a retry loop (up to `10 * childCount` attempts per frame):

```dart
// Simplified structure of RenderViewport.performLayout:
do {
  correction = _attemptLayout(mainAxisExtent, crossAxisExtent, offset.pixels + centerOffsetAdjustment);
  if (correction != 0.0) {
    offset.correctBy(correction); // silent mid-layout adjustment; try again!
    continue;
  }
} while (!offset.applyContentDimensions(minScrollExtent, maxScrollExtent));
```

Whenever a sliver reports a non-zero `geometry.scrollOffsetCorrection` — or `applyContentDimensions` adjusts `pixels` because the content shrank — `RenderViewport` corrects `offset` silently and re-runs `_attemptLayout` within the *same* layout pass so no broken intermediate frame ever reaches the screen.

## `center` and `anchor`

Normally a `Viewport` lays out all its slivers in the forward direction starting from `pixels == 0.0`. Two properties on `CustomScrollView` / `Viewport` unlock bidirectional and anchored layouts:

- **`center`** (`Key?`) points to one child sliver as the `0.0` origin. Slivers *after* `center` lay out forward (`pixels >= 0`); slivers *before* `center` lay out in reverse (`pixels < 0`, producing a negative `minScrollExtent`). Chat apps use `center` so prepending older messages above the origin never shifts `pixels` for newer messages below it.
- **`anchor`** (`0.0` to `1.0`, default `0.0`) shifts where `0.0` sits inside the viewport window. `anchor: 0.5` places the `center` sliver's leading edge dead-center in the viewport instead of flush against the top edge.

## What `shrinkWrap: true` Really Does

Normally `RenderViewport` sizes itself to `constraints.biggest` — it fills the screen height handed down by its parent without asking slivers how tall all their items are.

When you set `shrinkWrap: true` on a `ListView` or `CustomScrollView`, Flutter swaps `Viewport` out for `ShrinkWrappingViewport` (`RenderShrinkWrappingViewport`), which must size itself to the *sum of its slivers' content* (up to `constraints.maxHeight`):

- To know its own height, `RenderShrinkWrappingViewport` passes `remainingPaintExtent: double.infinity` (when unbounded) and walks slivers until their extents are known.
- **Lazy builders lose virtualization when shrink-wrapped inside unbounded constraints.** Putting `ListView.builder(shrinkWrap: true, physics: NeverScrollableScrollPhysics(), ...)` inside another `ListView` forces Flutter to build every single item in the inner list on the first frame. Replace that inner `ListView` with a `SliverList` inside one shared `CustomScrollView` instead.

## Common Pitfalls

**Putting a `ListView` inside a `Column` without `Expanded`.** `Column` passes `maxHeight: double.infinity` to its children, and `RenderViewport` tries to fill `constraints.biggest` — throwing `"Vertical viewport was given unbounded height"`. Wrap the `ListView` in `Expanded` or `Flexible` so it receives a finite height.

**Using `IntrinsicHeight` inside or around a `Viewport`.** Slivers depend on a scroll offset to decide which children exist, so `RenderViewport` cannot compute intrinsic dimensions and throws if an ancestor asks for `getMinIntrinsicHeight` / `getMaxIntrinsicHeight`.

That's `Viewport` end to end: `SingleChildScrollView` repaints one pre-laid-out `RenderBox`, `RenderViewport` lays out slivers lazily around `pixels` (with mid-layout correction retries), and `ShrinkWrappingViewport` trades lazy sizing for content-hugging bounds. Next, we'll open up the sliver layout protocol itself: `SliverConstraints` in, `SliverGeometry` out.
