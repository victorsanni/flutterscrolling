---
title: Sticky Header Sliver
nav: Sticky Header
description: Custom RenderSliver that scrolls to the leading edge and pins in place.
card: A 50-line RenderSliverSingleBoxAdapter that reveals how scrollExtent, paintExtent, and layoutExtent work together.
scripts: demos.js
---

A custom sliver (`StickyHeader` + `RenderStickyHeader`) that scrolls upward with normal content until its top edge reaches the top of the viewport, then stays pinned there while the `SliverList` after it slides smoothly underneath.

## Why Write a Sticky Header Sliver?

Flutter ships `PinnedHeaderSliver` out of the box, so in production code you rarely need to write this class yourself. Writing it once is the fastest way to make the sliver protocol click: almost every confusing field on `SliverConstraints` and `SliverGeometry` — `scrollOffset`, `overlap`, `scrollExtent`, `paintExtent`, `layoutExtent`, and `childMainAxisPosition` — has one clear, visible job here.

## Try it Out

Drag the list or jump to the preset offsets and watch `geometry.layoutExtent` shrink from `44.0` down to `0.0` while `geometry.paintExtent` stays `44.0`.

<div class="demo" data-demo="sticky">
<div class="demo-stage">
<div class="demo-view"><canvas width="260" height="250"></canvas></div>
<div class="demo-side">
<div class="demo-heading">RenderStickyHeader</div>
<table class="demo-readout">
<tr><td>constraints.scrollOffset</td><td data-f="scrollOffset">0.0</td></tr>
<tr><td>remainingPaintExtent</td><td data-f="remaining">154.0</td></tr>
<tr><td>geometry.scrollExtent</td><td data-f="scrollExtent">44.0</td></tr>
<tr><td>geometry.paintExtent</td><td data-f="paintExtent">44.0</td></tr>
<tr><td>geometry.layoutExtent</td><td class="hot" data-f="layoutExtent">44.0</td></tr>
</table>
</div>
</div>
<div class="demo-controls">
<label>Jump</label>
<button class="demo-btn" type="button" data-jump="0">Top (0px)</button>
<button class="demo-btn" type="button" data-jump="96">Touch top (96px)</button>
<button class="demo-btn" type="button" data-jump="118">Halfway (118px)</button>
<button class="demo-btn" type="button" data-jump="240">Pinned (240px)</button>
</div>
<div class="demo-note">Once <code>scrollOffset</code> passes <code>44.0</code>, <code>layoutExtent</code> hits <code>0.0</code> so the list lays out right at the top and slides underneath.</div>
</div>

## The Implementation

### Extending `RenderSliverSingleBoxAdapter`

A sliver cannot host a `RenderBox` child without a bridge between `SliverConstraints` and `BoxConstraints`. Extending `RenderSliverSingleBoxAdapter` gives you single-child management, painting, hit-testing, and `applyPaintTransform` for free — leaving just two methods to implement: `childMainAxisPosition` and `performLayout`.

```dart
class RenderStickyHeader extends RenderSliverSingleBoxAdapter {
  RenderStickyHeader({super.child});

  @override
  double childMainAxisPosition(RenderBox child) => 0.0;
```

In a normal `SliverToBoxAdapter`, `childMainAxisPosition` returns `-constraints.scrollOffset` so the child slides out of view as `scrollOffset` grows. Returning `0.0` keeps the child anchored to the sliver's own origin at all times.

### Splitting `layoutExtent` from `paintExtent`

Before the header reaches the top of the viewport, `constraints.scrollOffset` is `0.0`: earlier slivers absorbed the scroll offset, and the viewport placed this sliver right below them. Once the earlier slivers have scrolled completely off-screen, `constraints.scrollOffset` starts climbing from `0.0` upward.

That is the moment `layoutExtent` and `paintExtent` diverge:

- `paintExtent` stays equal to `childExtent` (say `56.0`), because the header is still drawn in full at the top of the viewport.
- `layoutExtent` shrinks as `childExtent - constraints.scrollOffset`, clamped to `0.0`. `RenderViewport` advances the *next* sliver's starting position by `layoutExtent`, not `paintExtent` — so as `layoutExtent` shrinks to zero, the `SliverList` moves up underneath the still-painted header.

```dart
final double layoutExtent = clampDouble(
  childExtent - constraints.scrollOffset,
  0.0,
  constraints.remainingPaintExtent,
);

final double paintExtent = math.min(
  childExtent,
  constraints.remainingPaintExtent - constraints.overlap,
);
```

### Playing Nicely With Other Slivers

Three smaller fields on `SliverGeometry` make the header cooperate with sibling slivers and `Scrollable.ensureVisible`:

- `paintOrigin: constraints.overlap` shifts this header *after* any earlier pinned sliver so two consecutive sticky headers stack cleanly instead of painting on top of one another.
- `maxScrollObstructionExtent: childExtent` tells `RenderViewport.getOffsetToReveal` that the top `56px` of the viewport is permanently covered, so `ensureVisible` scrolls target items *below* the pinned header rather than hiding them behind it.
- `hasVisualOverflow: true` lets `RenderSliverSingleBoxAdapter` know the sliver paints past its `layoutExtent`.

```dart
geometry = SliverGeometry(
  scrollExtent: childExtent,
  paintOrigin: constraints.overlap,
  paintExtent: paintExtent,
  layoutExtent: layoutExtent,
  maxPaintExtent: childExtent,
  maxScrollObstructionExtent: childExtent,
  cacheExtent: calculateCacheOffset(
    constraints,
    from: 0.0,
    to: childExtent,
  ),
  hasVisualOverflow: true,
);
```

## Full Source Code

```dart
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/widgets.dart';

/// A sliver that scrolls with the content until it reaches the leading edge
/// of the viewport, and then stays there.
///
/// The framework ships the same behavior as [PinnedHeaderSliver]. This one is
/// written out in full so every line of the sliver protocol is visible.
class StickyHeader extends SingleChildRenderObjectWidget {
  const StickyHeader({super.key, super.child});

  @override
  RenderStickyHeader createRenderObject(BuildContext context) =>
      RenderStickyHeader();
}

class RenderStickyHeader extends RenderSliverSingleBoxAdapter {
  RenderStickyHeader({super.child});

  double get _childExtent {
    final RenderBox? child = this.child;
    if (child == null) {
      return 0.0;
    }
    return switch (constraints.axis) {
      Axis.vertical => child.size.height,
      Axis.horizontal => child.size.width,
    };
  }

  // The child is always drawn at the sliver's own origin. It never slides
  // out from under the sliver the way a normal scrolling child does.
  @override
  double childMainAxisPosition(RenderBox child) => 0.0;

  @override
  void performLayout() {
    final SliverConstraints constraints = this.constraints;
    child?.layout(constraints.asBoxConstraints(), parentUsesSize: true);
    final double childExtent = _childExtent;

    // How much room the header still takes from the slivers after it. Once
    // it has scrolled a full header's height, it takes none: the next sliver
    // lays out as if the header were gone, and slides underneath it.
    final double layoutExtent = clampDouble(
      childExtent - constraints.scrollOffset,
      0.0,
      constraints.remainingPaintExtent,
    );

    // How much the header draws: all of itself, if the viewport has room.
    final double paintExtent = math.min(
      childExtent,
      constraints.remainingPaintExtent - constraints.overlap,
    );

    geometry = SliverGeometry(
      // The header is one header tall in the scrollable content.
      scrollExtent: childExtent,
      // Start drawing after any earlier pinned sliver, not underneath it.
      paintOrigin: constraints.overlap,
      paintExtent: paintExtent,
      layoutExtent: layoutExtent,
      maxPaintExtent: childExtent,
      // Tells reveal logic that this much of the viewport stays covered.
      maxScrollObstructionExtent: childExtent,
      cacheExtent: calculateCacheOffset(
        constraints,
        from: 0.0,
        to: childExtent,
      ),
      // The header can paint past its layout extent, over the next sliver.
      hasVisualOverflow: true,
    );
  }
}

/// A scroll view with a title that scrolls away, a header that sticks, and a
/// long list.
class StickyHeaderDemo extends StatelessWidget {
  const StickyHeaderDemo({super.key, this.controller});

  final ScrollController? controller;

  @override
  Widget build(BuildContext context) {
    return CustomScrollView(
      controller: controller,
      slivers: <Widget>[
        const SliverToBoxAdapter(
          child: SizedBox(
            height: 120.0,
            child: Center(
              child: Text('Scrolls away', style: TextStyle(fontSize: 24.0)),
            ),
          ),
        ),
        const StickyHeader(
          child: ColoredBox(
            color: Color(0xFF12A6AD),
            child: SizedBox(
              height: 56.0,
              child: Center(
                child: Text(
                  'Sticks',
                  style: TextStyle(color: Color(0xFFFFFFFF), fontSize: 18.0),
                ),
              ),
            ),
          ),
        ),
        SliverList.builder(
          itemCount: 40,
          itemBuilder: (BuildContext context, int index) {
            return SizedBox(
              height: 48.0,
              child: Center(child: Text('Row $index')),
            );
          },
        ),
      ],
    );
  }
}
```

## Similar Implementations

- `_RenderPinnedHeaderSliver` in `package:flutter/src/widgets/pinned_header_sliver.dart` is the framework's production version of this exact sliver, adding semantics scrolling exclusion and explicit clip handling.
- `RenderSliverPinnedPersistentHeader` in `package:flutter/src/rendering/sliver_persistent_header.dart` adds shrinking between `maxExtent` and `minExtent` on top of the same `layoutExtent` vs `paintExtent` split.
