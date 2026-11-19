// Example 3: a sliver that scrolls normally, then sticks to the top.
//
// Walkthrough: site/examples/sticky-header.html

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
