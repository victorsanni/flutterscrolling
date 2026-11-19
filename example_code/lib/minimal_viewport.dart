// Example 2: the smallest useful viewport, driven by a Scrollable.
//
// Walkthrough: site/examples/minimal-viewport.html

import 'dart:math' as math;

import 'package:flutter/rendering.dart';
import 'package:flutter/widgets.dart';

/// A vertical scroll view built from nothing but [Scrollable] and one custom
/// render object.
class BareScrollView extends StatelessWidget {
  const BareScrollView({
    super.key,
    this.controller,
    this.physics,
    required this.child,
  });

  final ScrollController? controller;
  final ScrollPhysics? physics;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scrollable(
      controller: controller,
      physics: physics,
      viewportBuilder: (BuildContext context, ViewportOffset offset) {
        return BareViewport(offset: offset, child: child);
      },
    );
  }
}

/// Shows a window onto a single child that may be taller than the window.
class BareViewport extends SingleChildRenderObjectWidget {
  const BareViewport({super.key, required this.offset, super.child});

  /// How far the child is scrolled. In practice, the [ScrollPosition] that a
  /// [Scrollable] hands to its viewport builder.
  final ViewportOffset offset;

  @override
  RenderBareViewport createRenderObject(BuildContext context) {
    return RenderBareViewport(offset: offset);
  }

  @override
  void updateRenderObject(
    BuildContext context,
    RenderBareViewport renderObject,
  ) {
    renderObject.offset = offset;
  }

  @override
  SingleChildRenderObjectElement createElement() => _BareViewportElement(this);
}

// Counts this viewport in the `depth` of scroll notifications that bubble
// through it, the same way the framework's own viewports do.
class _BareViewportElement extends SingleChildRenderObjectElement
    with NotifiableElementMixin, ViewportElementMixin {
  _BareViewportElement(BareViewport super.widget);
}

class RenderBareViewport extends RenderBox
    with RenderObjectWithChildMixin<RenderBox> {
  RenderBareViewport({required ViewportOffset offset}) : _offset = offset;

  ViewportOffset get offset => _offset;
  ViewportOffset _offset;
  set offset(ViewportOffset value) {
    if (value == _offset) {
      return;
    }
    if (attached) {
      _offset.removeListener(markNeedsPaint);
    }
    _offset = value;
    if (attached) {
      _offset.addListener(markNeedsPaint);
    }
    // A new offset object needs to be told the dimensions again.
    markNeedsLayout();
  }

  // Scrolling moves the child; it never changes anyone's size. So a scroll
  // only needs a repaint.
  @override
  void attach(PipelineOwner owner) {
    super.attach(owner);
    _offset.addListener(markNeedsPaint);
  }

  @override
  void detach() {
    _offset.removeListener(markNeedsPaint);
    super.detach();
  }

  // Keeps those repaints from spreading to our ancestors.
  @override
  bool get isRepaintBoundary => true;

  double get _maxScrollExtent {
    final RenderBox? child = this.child;
    return child == null ? 0.0 : math.max(0.0, child.size.height - size.height);
  }

  @override
  void performLayout() {
    final RenderBox? child = this.child;
    if (child == null) {
      size = constraints.smallest;
    } else {
      // The child keeps our width limits but may be as tall as it likes.
      child.layout(constraints.widthConstraints(), parentUsesSize: true);
      size = constraints.constrain(child.size);
    }

    // The window or the content may have shrunk under the current offset.
    if (offset.hasPixels && offset.pixels > _maxScrollExtent) {
      offset.correctBy(_maxScrollExtent - offset.pixels);
    }

    // The whole contract with the scroll position, in two calls.
    offset.applyViewportDimension(size.height);
    offset.applyContentDimensions(0.0, _maxScrollExtent);
  }

  Offset get _paintOffset => Offset(0.0, -offset.pixels);

  @override
  void paint(PaintingContext context, Offset offset) {
    final RenderBox? child = this.child;
    if (child == null) {
      return;
    }
    final Offset paintOffset = _paintOffset;
    _clipRectLayer.layer = context.pushClipRect(
      needsCompositing,
      offset,
      Offset.zero & size,
      (PaintingContext context, Offset offset) {
        context.paintChild(child, offset + paintOffset);
      },
      oldLayer: _clipRectLayer.layer,
    );
  }

  final LayerHandle<ClipRectLayer> _clipRectLayer =
      LayerHandle<ClipRectLayer>();

  @override
  void dispose() {
    _clipRectLayer.layer = null;
    super.dispose();
  }

  // Paint, transforms and hit testing must agree on where the child is.
  @override
  void applyPaintTransform(RenderBox child, Matrix4 transform) {
    final Offset paintOffset = _paintOffset;
    transform.translateByDouble(paintOffset.dx, paintOffset.dy, 0.0, 1.0);
  }

  @override
  bool hitTestChildren(BoxHitTestResult result, {required Offset position}) {
    final RenderBox? child = this.child;
    if (child == null) {
      return false;
    }
    return result.addWithPaintOffset(
      offset: _paintOffset,
      position: position,
      hitTest: (BoxHitTestResult result, Offset transformed) {
        return child.hitTest(result, position: transformed);
      },
    );
  }
}
