---
title: Minimal Viewport
nav: Minimal Viewport
description: Custom RenderBox viewport driven directly by Scrollable and ViewportOffset.
card: A complete vertical scroll view built from Scrollable and one 100-line RenderBox — no slivers involved.
scripts: demos.js
---

A complete vertical scroll view built from `Scrollable` and a single custom `RenderBox` (`RenderBareViewport`). It lays out one tall child, reports the viewport and content dimensions to the `ViewportOffset`, shifts the child by `-offset.pixels` at paint time, clips to its own bounds, and translates pointer hits to match.

## Why Build a Bare Viewport?

Between `ListView`, `CustomScrollView`, `RenderViewport`, and a dozen sliver classes, it is easy to assume scrolling is deeply wired into slivers. Building a working scroll view without a single sliver strips away all of that machinery and shows the exact contract between `Scrollable` and whatever renders the content.

It is also the real architecture behind `SingleChildScrollView`, which uses a private `_RenderSingleChildViewport` rather than a sliver `Viewport` when all you have is one `RenderBox` child that fits comfortably in memory.

## Try it Out

Drag the list up and down, click any visible item to test hit-testing through the scroll offset, and toggle `ClipRect` off to peek at how the full child is positioned behind the window.

<div class="demo" data-demo="viewport">
<div class="demo-stage">
<div class="demo-view"><canvas width="260" height="250"></canvas></div>
<div class="demo-side">
<div class="demo-heading">RenderBareViewport</div>
<table class="demo-readout">
<tr><td>offset.pixels</td><td data-f="pixels">84.0</td></tr>
<tr><td>_paintOffset</td><td class="hot" data-f="paintOffset">(0.0, -84.0)</td></tr>
<tr><td>viewportDimension</td><td data-f="viewportDim">178.0</td></tr>
<tr><td>maxScrollExtent</td><td data-f="maxExtent">242.0</td></tr>
<tr><td>hitTestChildren</td><td data-f="hit">Item 2</td></tr>
</table>
</div>
</div>
<div class="demo-controls">
<label>Compositing</label>
<button class="demo-btn on" type="button" data-action="toggle-clip">ClipRect: on</button>
</div>
<div class="demo-note">Drag to scroll; click a row inside the frame to run <code>addWithPaintOffset</code> hit-testing.</div>
</div>

## The Implementation

### Connecting `Scrollable` to the Viewport

`Scrollable` handles drag gestures, wheel events, physics, ballistic flings, scrollbars, and overscroll indicators. All it asks from you is a `viewportBuilder` callback that accepts a `ViewportOffset` and returns the widget that paints the window.

```dart
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
```

Mixing `ViewportElementMixin` into `BareViewport`'s element increments `ScrollNotification.depth` as notifications bubble past this viewport, matching the behavior of Flutter's built-in viewports when scroll views are nested.

### Listening to `ViewportOffset` for Repaints Only

Because `RenderBareViewport` lays out its single child in full up front, scrolling never changes the child's size or layout. Attaching `markNeedsPaint` (not `markNeedsLayout`) as the listener on `offset` means every scroll frame skips layout completely and only repaints inside this render object's own repaint boundary.

```dart
@override
void attach(PipelineOwner owner) {
  super.attach(owner);
  _offset.addListener(markNeedsPaint);
}

@override
bool get isRepaintBoundary => true;
```

### Reporting Dimensions in `performLayout`

During `performLayout`, the child gets the parent's width constraints and an unbounded height (`constraints.widthConstraints()`), then `RenderBareViewport` constrains its own size to the incoming box constraints. Before returning, it fulfills the entire `ViewportOffset` contract in two calls: `applyViewportDimension` and `applyContentDimensions`.

```dart
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
```

If the child shrank while scrolled near the bottom, `offset.correctBy(...)` silently pulls `pixels` back into range *without* notifying listeners mid-layout.

### Painting, Transforms, and Hit Testing

When `offset.pixels` is `+150.0`, the user has scrolled `150px` down into the content, so the child must be painted `150px` *upward* at `Offset(0.0, -offset.pixels)`. Three methods must agree on that exact `_paintOffset`: `paint`, `applyPaintTransform`, and `hitTestChildren`.

```dart
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
```

Reusing `_clipRectLayer.layer` via `LayerHandle<ClipRectLayer>` avoids allocating a fresh engine clip layer on every frame, and `result.addWithPaintOffset` subtracts `_paintOffset` from incoming tap coordinates so taps hit the row actually drawn under the finger.

## Full Source Code

```dart
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
```

## Similar Implementations

- `_RenderSingleChildViewport` in `package:flutter/src/widgets/single_child_scroll_view.dart` adds horizontal axis directions, `reverse`, `clipBehavior`, and `RenderAbstractViewport` reveal support on top of this exact skeleton.
- `RenderListWheelViewport` in `package:flutter/src/rendering/list_wheel_viewport.dart` connects to `ViewportOffset` the same way while painting children wrapped around a 3D cylinder instead of a flat plane.
