---
title: SliverConstraints
nav: SliverConstraints
description: Read SliverConstraints inside RenderSliver.performLayout() or SliverLayoutBuilder.
---

`SliverConstraints` is the input object handed down by `RenderViewport` (or an enclosing adapter sliver such as `RenderSliverPadding`) to a `RenderSliver` on every layout pass.

## Key Properties

| Property | Type | Meaning |
| --- | --- | --- |
| `axisDirection` / `axis` | `AxisDirection` / `Axis` | Main scroll direction (`down`, `up`, `right`, `left`) |
| `growthDirection` | `GrowthDirection` | `forward` after `center` key, `reverse` before `center` key |
| `userScrollDirection` | `ScrollDirection` | Most recent user drag direction (`forward`, `reverse`, `idle`) |
| `scrollOffset` | `double` | Pixels of *this sliver* scrolled past the leading edge (`>= 0.0`) |
| `precedingScrollExtent` | `double` | Sum of `scrollExtent` of all earlier slivers (`>= 0.0`) |
| `overlap` | `double` | Pixels at this sliver's start covered by earlier pinned/floating slivers |
| `remainingPaintExtent` | `double` | Visible viewport space remaining from this sliver's start (`>= 0.0`) |
| `crossAxisExtent` | `double` | Viewport width (when vertical) or height (when horizontal) |
| `viewportMainAxisExtent` | `double` | Full main-axis length of the viewport window |
| `cacheOrigin` | `double` | Start of cache region relative to `scrollOffset` (`<= 0.0`, e.g. `-250.0`) |
| `remainingCacheExtent` | `double` | Total length from `cacheOrigin` to trailing cache edge |

## Convert to `BoxConstraints` for a Child `RenderBox`

Example using `asBoxConstraints` inside a `RenderSliver` to tighten the cross axis while leaving the main axis unconstrained (or bounded).

```dart
// Unbounded main-axis extent, tight cross-axis extent:
child!.layout(constraints.asBoxConstraints(), parentUsesSize: true);

// Tight main-axis extent of exactly 64.0 logical pixels:
child!.layout(
  constraints.asBoxConstraints(minExtent: 64.0, maxExtent: 64.0),
  parentUsesSize: true,
);
```

## Responsive Sliver Grid Columns (`SliverLayoutBuilder`)

Example of reading `SliverConstraints.crossAxisExtent` in widget code without writing a custom `RenderSliver`.

```dart
SliverLayoutBuilder(
  builder: (BuildContext context, SliverConstraints constraints) {
    final int columns = (constraints.crossAxisExtent / 180.0).floor().clamp(1, 6);
    return SliverGrid.builder(
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: columns,
        mainAxisSpacing: 12.0,
        crossAxisSpacing: 12.0,
      ),
      itemCount: items.length,
      itemBuilder: itemBuilder,
    );
  },
)
```

## Check Whether This Sliver Has Reached the Pinned Edge

Example inside `performLayout` checking whether the leading edge (or an earlier pinned header's bottom edge) has touched this sliver.

```dart
final bool isAtOrPastTop = constraints.scrollOffset > 0.0 || constraints.overlap > 0.0;
```
