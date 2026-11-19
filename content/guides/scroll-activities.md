---
title: Scroll Activities
nav: Scroll Activities
description: The five runtime states a ScrollPosition moves through — Idle, Hold, Drag, Ballistic, and Driven.
---

This guide walks experienced Flutter developers through `ScrollActivity` and how a `ScrollPosition` transitions from resting, to held, to dragged, to coasting. By the end, you'll understand why activities exist separately from `ScrollPhysics`, what happens in each of the five built-in activities, and how momentum carries across consecutive flicks on iOS. We'll skip widget-level `ScrollController` APIs and sliver layout — this is about the position's state machine, and only its state machine.

## What This Guide Covers

- **Why Activities Exist Alongside Physics** — The clean split between stateless `ScrollPhysics` math and stateful per-gesture `ScrollActivity` drivers.
- **The Five Built-in Activities** — `IdleScrollActivity`, `HoldScrollActivity`, `DragScrollActivity`, `BallisticScrollActivity`, and `DrivenScrollActivity`.
- **How Transitions Emit Notifications** — Why `beginActivity` is where `ScrollStartNotification`, `ScrollEndNotification`, and `isScrollingNotifier` actually fire.
- **Carried Momentum on Touch Down** — How catching a fast fling with your thumb transfers speed into the next flick.
- **When You Don't Need to Touch Activities** — Why custom scrolling almost never subclasses `ScrollActivity`.

## Why Activities Exist Alongside Physics

`ScrollPhysics` is `const` and stateless — it cannot hold an `AnimationController`, a `Completer` for `animateTo`, or an active drag handle.

`ScrollActivity` is the stateful counterpart owned by `ScrollPosition`. **A `ScrollPosition` has exactly one active `ScrollActivity` at every moment**, and replacing that activity via `beginActivity` disposes the old driver cleanly before starting the new one.

{{figure:activity-states|A normal touch gesture walks Idle -> Hold -> Drag -> Ballistic -> Idle; programmatic animateTo runs Driven -> Ballistic -> Idle.}}

## The Five Built-in Activities

`ScrollPositionWithSingleContext` rotates among five concrete activity classes:

1. **`IdleScrollActivity`** — The position is at rest. `isScrolling` is `false`, `velocity` is `0.0`, and no ticker is running. Calling `goIdle()` enters this state.
2. **`HoldScrollActivity`** — A pointer has touched down on the scrollable (`position.hold(...)`), stopping any in-flight fling, **but hasn't dragged far enough to win the gesture arena yet.** `isScrolling` is `false`. If the user lifts their finger without dragging (a tap), the hold cancels and calls `goBallistic(0.0)` so an overscrolled list can finish springing back.
3. **`DragScrollActivity`** — Paired with a `ScrollDragController` once the drag gesture recognizer wins. `isScrolling` is `true`, `velocity` reports `0.0` (velocity is tracked by the gesture recognizer until liftoff), and pointer movements drive `applyUserOffset`.
4. **`BallisticScrollActivity`** — Runs an `AnimationController.unbounded` driven by a `Simulation` from `physics.createBallisticSimulation`. On every tick it calls `setPixels(simulation.x(elapsed))`. If `setPixels` returns non-zero overscroll (meaning `ClampingScrollPhysics` hit a hard wall), the activity stops immediately and calls `goIdle()`.
5. **`DrivenScrollActivity`** — Created by `animateTo(to, duration: ..., curve: ...)`. Drives an `AnimationController` from the current `pixels` to `to` over `duration` with `curve`, completes the `Future<void>` returned by `animateTo`, and finishes with `goBallistic(0.0)` so jumping or animating out of bounds still settles cleanly.

```dart
// Inside ScrollPositionWithSingleContext.animateTo:
final DrivenScrollActivity activity = DrivenScrollActivity(
  this,
  from: pixels,
  to: to,
  duration: duration,
  curve: curve,
  vsync: context.vsync,
);
beginActivity(activity);
return activity.done;
```

## How Transitions Emit Notifications

Every state change funnels through `ScrollPosition.beginActivity(ScrollActivity? newActivity)`. Comparing `wasScrolling` (on the outgoing activity) with `isScrolling` (on the incoming activity) is what drives both `isScrollingNotifier` and lifecycle notifications:

- **`!wasScrolling && isScrolling`** (for example, `Hold` → `Drag` or `Idle` → `Driven`) sets `isScrollingNotifier.value = true` and dispatches `ScrollStartNotification`.
- **`wasScrolling && isScrolling`** (for example, `Drag` → `Ballistic` at finger liftoff) keeps `isScrollingNotifier.value = true` — **no `ScrollEndNotification` fires between the drag and its fling.** From listeners' perspective, one continuous scroll is still underway.
- **`wasScrolling && !isScrolling`** (for example, `Ballistic` → `Idle`, or catching a `Ballistic` fling with a finger into `Hold`) sets `isScrollingNotifier.value = false` and dispatches `ScrollEndNotification`.

That middle transition explains a subtle behavior that surprises many developers: lifting your finger at the end of a flick does *not* emit `ScrollEndNotification` until the resulting ballistic simulation comes to rest (or is interrupted).

## Carried Momentum on Touch Down

Have you ever flicked a long list on iOS, caught it mid-flight with your thumb, and flicked again to go even faster? That happens during the `Ballistic` → `Hold` transition:

```dart
// Simplified from ScrollPositionWithSingleContext.hold:
final double previousVelocity = activity!.velocity;
beginActivity(HoldScrollActivity(delegate: this, onHoldCanceled: cancelCallback));
_heldPreviousVelocity = previousVelocity;
```

When `BallisticScrollActivity` is replaced by `HoldScrollActivity`, the position records `previousVelocity` in `_heldPreviousVelocity`. If the user immediately drags in the *same* direction and lifts off again, `ScrollDragController.end` asks `physics.carriedMomentum(_heldPreviousVelocity)` (`BouncingScrollPhysics` returns a fraction of that prior speed) and adds it to the new fling's launch velocity.

## When You Don't Need to Touch Activities

In normal Flutter development, **you never instantiate or subclass `ScrollActivity`.**

- Want custom deceleration, snapping, or spring constants? Override `createBallisticSimulation` on `ScrollPhysics` — `BallisticScrollActivity` will run whatever `Simulation` you return.
- Want custom duration/curve scrolling? Call `controller.animateTo(...)` — `DrivenScrollActivity` runs it for you.
- Want to know when scrolling starts and stops without a `NotificationListener`? Listen to `controller.position.isScrollingNotifier`, which flips between `true` and `false` right inside `beginActivity`.

Only framework-level coordinators like `NestedScrollView` write custom `ScrollActivity` subclasses because they split a single ballistic simulation across an outer header position and an inner body position simultaneously.

## Common Pitfalls

**Assuming `animateTo`'s `Future` waits if a user grabs the list.** Actually, `DrivenScrollActivity.done` *does* complete when interrupted by a user touch (inside `dispose()`), even though the destination offset `to` was never reached. Never assume `controller.offset == targetOffset` just because `await controller.animateTo(targetOffset, ...)` returned — check `controller.offset` afterward if exact arrival matters.

**Expecting `ScrollEndNotification` on finger up.** Lifting your finger transitions from `DragScrollActivity` (`isScrolling == true`) to `BallisticScrollActivity` (`isScrolling == true`). `ScrollEndNotification` only fires when `BallisticScrollActivity` finishes (or if `createBallisticSimulation` returns `null`, transitioning straight to `IdleScrollActivity`).

That's `ScrollActivity` end to end: one active driver at a time on `ScrollPosition`, transitioning cleanly via `beginActivity` from `Idle` through `Hold`, `Drag`, `Ballistic`, and `Driven`. Next, we'll step up to the widget API you hold in your own state classes: `ScrollController` and `PrimaryScrollController`.
