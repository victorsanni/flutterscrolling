---
title: How Scrolling Works
nav: How Scrolling Works
description: Four small pieces passing one number around — the whole scrolling pipeline on one page.
card: A scroll view looks like one big widget. Under the hood, it is four small classes passing a single pixel offset around.
---

This guide walks experienced Flutter developers through the end-to-end architecture of a Flutter scroll view. By the end, you'll understand which class owns gestures, which class owns the scroll offset, which class enforces edge rules, and which class paints the visible window. We'll skip sliver geometry fields, lazy child garbage collection, and custom physics math for now — this is about how the pieces fit together, and only how they fit together.

## What This Guide Covers

- **One Number in the Middle** — Why all of Flutter scrolling reduces to reading and updating a single `double` called `pixels`.
- **The Four Pieces** — The distinct jobs of `Scrollable`, `ScrollPosition`, `ScrollPhysics`, and `Viewport`.
- **Following One Drag Frame** — What happens, call by call, when your finger moves `12` logical pixels up the screen.
- **Following Liftoff** — How a drag hands off to a ballistic simulation when your finger leaves the glass.
- **What You Rarely Need to Touch** — Which pieces you customize in everyday apps and which ones you almost never subclass.

## One Number in the Middle

Scrolling in Flutter is the management of a single `double` named `pixels`: how many logical pixels of content currently sit *before* the leading edge of the viewport.

When a vertical list starts at the top, `pixels` is `0.0`. Dragging your finger upward by `180` pixels pushes `180` pixels of content above the top edge of the window, so `pixels` becomes `180.0`. Every scrollbar thumb, pinned header, lazy list builder, and overscroll glow on screen is just reacting to that one number.

{{figure:four-pieces|Scrollable turns input into deltas, ScrollPosition owns pixels, ScrollPhysics governs legal movement, and Viewport paints the window and reports dimensions back.}}

## The Four Pieces

Every scroll view in Flutter — `SingleChildScrollView`, `ListView`, `GridView`, `CustomScrollView`, `PageView` — assembles the same four collaborators:

1. `Scrollable` is a `StatefulWidget` that listens to drag gestures and pointer wheel events, wraps the tree in scrollbars and overscroll indicators from `ScrollBehavior`, and owns the lifecycle of the `ScrollPosition`.
2. `ScrollPosition` (specifically `ScrollPositionWithSingleContext` in standard scroll views) is a `Listenable` object that holds `pixels`, the viewport size, the content bounds, and the active `ScrollActivity`.
3. `ScrollPhysics` is an immutable strategy object that answers stateless math questions for the position: how much a user drag moves `pixels`, whether `pixels` may cross an edge, and what `Simulation` runs after liftoff.
4. `Viewport` (and its `RenderViewport` render object) lays out visible slivers at the current `pixels` offset, clips and paints them, and reports `viewportDimension` and `minScrollExtent` / `maxScrollExtent` back to the `ScrollPosition`.

```dart
Scrollable(
  controller: controller,
  physics: const BouncingScrollPhysics(),
  viewportBuilder: (BuildContext context, ViewportOffset offset) {
    // `offset` is the ScrollPosition itself, typed as ViewportOffset.
    return Viewport(
      offset: offset,
      slivers: slivers,
    );
  },
)
```

Notice the narrow type in `viewportBuilder`: `Viewport` receives the `ScrollPosition` typed as its superclass `ViewportOffset`. **The render layer never imports `ScrollController`, `ScrollPhysics`, or `Scrollable`.** All `RenderViewport` sees is an observable `pixels` value and two callbacks for reporting dimensions back.

## Following One Drag Frame

Trace what happens when a user places a finger on a vertical `ListView` and moves it upward by `12.0` pixels (`primaryDelta == -12.0`):

1. `VerticalDragGestureRecognizer` (installed by `ScrollableState`) wins the gesture arena and calls `ScrollDragController.update` with `details.primaryDelta = -12.0`.
2. `ScrollDragController` forwards that delta to `ScrollPositionWithSingleContext.applyUserOffset(-12.0)`.
3. The position asks `physics.applyPhysicsToUserOffset(this, -12.0)`. Inside normal bounds this returns `-12.0` unchanged; when already overscrolled on iOS, `BouncingScrollPhysics` scales it down so pulling feels progressively stiffer.
4. The position calls `setPixels(pixels - (-12.0))`, proposing `pixels + 12.0` (dragging *up* increases `pixels`).
5. Inside `setPixels`, `physics.applyBoundaryConditions(this, proposedPixels)` returns how much of the move is refused. If `0.0` is refused, `_pixels` updates, `notifyListeners()` fires, and a `ScrollUpdateNotification` bubbles up the widget tree.
6. `RenderViewport`, which registered `markNeedsLayout` as a listener on `ViewportOffset`, lays out slivers at the new offset during the next frame and paints the shifted content.

> **Aside:** The sign flip in step 4 trips up everyone the first time they read the Flutter source. Pointer deltas are in screen coordinates (finger moving up is `-12.0`), while scroll offsets measure content scrolled past the top (`+12.0`). `applyUserOffset` bridges the two with `pixels - delta`.

## Following Liftoff

When the finger leaves the screen with upward velocity, `VerticalDragGestureRecognizer` fires `onEnd` with a `DragEndDetails`. `ScrollDragController` hands the negated velocity (now positive pixels per second) to `position.goBallistic(velocity)`:

1. `ScrollPositionWithSingleContext.goBallistic` calls `physics.createBallisticSimulation(this, velocity)`.
2. On Android, `ClampingScrollPhysics` returns a `ClampingScrollSimulation` that decelerates under friction. On iOS, `BouncingScrollPhysics` returns a `BouncingScrollSimulation` that switches smoothly from friction into a return spring if it crosses `maxScrollExtent`.
3. If the simulation is non-null, the position starts a `BallisticScrollActivity`, which ticks an unbounded `AnimationController` every vsync frame and feeds `simulation.x(elapsedSeconds)` into `setPixels`.
4. When the simulation reports `isDone` (or hits a clamping wall), the activity calls `goIdle()`, switching the position back to `IdleScrollActivity` and dispatching `ScrollEndNotification`.

## What You Rarely Need to Touch

Because responsibilities are split cleanly across the four classes, almost every customization touches just one seam:

- **Read the offset or scroll programmatically** — pass a [ScrollController](/guides/scroll-controllers).
- **Change snapping, friction, or edge bounce** — subclass [ScrollPhysics](/guides/scroll-physics).
- **React to scrolling from an ancestor widget** — wrap in a `NotificationListener` for [Scroll Notifications](/guides/scroll-notifications).
- **Build custom scrolling layouts** — compose slivers or write a `RenderSliver` ([Sliver Layout](/guides/sliver-layout)).

You almost never need to subclass `Scrollable`, `ScrollPosition`, or `ScrollActivity` yourself.

## Mental Model Summary

- **One source of truth:** `ScrollPosition.pixels` is the single number that defines where the scroll view is.
- **Input flows down into `ScrollPosition`:** `Scrollable` converts drag and wheel events into calls on the position.
- **Rules live on `ScrollPhysics`:** `ScrollPosition` asks `ScrollPhysics` before accepting a user delta, crossing an edge, or starting a fling.
- **Dimensions flow back from `Viewport`:** During layout, `RenderViewport` tells `ScrollPosition` how tall the window is (`viewportDimension`) and where content starts and ends (`minScrollExtent`, `maxScrollExtent`).
- **Rendering listens to `ViewportOffset`:** Mutating `pixels` notifies `RenderViewport` (or `_RenderSingleChildViewport`), scheduling the next layout or paint pass.

That's the whole scrolling machine from finger down to resting frame. Next, we'll look closely at `ScrollPosition` itself — the extents it tracks and the three very different methods that are allowed to change `pixels`.
