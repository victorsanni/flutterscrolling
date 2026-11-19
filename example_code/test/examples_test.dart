import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutterscrolling_examples/minimal_viewport.dart';
import 'package:flutterscrolling_examples/snapping_physics.dart';
import 'package:flutterscrolling_examples/sticky_header.dart';

void main() {
  group('SnapScrollPhysics', () {
    testWidgets('snaps to nearest item boundary after a slow drag', (
      WidgetTester tester,
    ) async {
      final ScrollController controller = ScrollController();
      addTearDown(controller.dispose);

      await tester.pumpWidget(
        Directionality(
          textDirection: TextDirection.ltr,
          child: SizedBox(
            width: 440.0,
            height: 200.0,
            child: SnappingCards(controller: controller),
          ),
        ),
      );

      // Drag slightly past half of the first 220px card, then hold so velocity ~ 0.
      final TestGesture gesture = await tester.startGesture(
        const Offset(300.0, 100.0),
      );
      await gesture.moveBy(const Offset(-140.0, 0.0));
      await tester.pump(const Duration(milliseconds: 200));
      await gesture.up();
      await tester.pumpAndSettle();

      expect(controller.offset, closeTo(SnappingCards.itemExtent, 0.5));
    });

    testWidgets('advances to the next item on a fling', (
      WidgetTester tester,
    ) async {
      final ScrollController controller = ScrollController();
      addTearDown(controller.dispose);

      await tester.pumpWidget(
        Directionality(
          textDirection: TextDirection.ltr,
          child: SizedBox(
            width: 440.0,
            height: 200.0,
            child: SnappingCards(controller: controller),
          ),
        ),
      );

      await tester.fling(
        find.byType(SnappingCards),
        const Offset(-60.0, 0.0),
        800.0,
      );
      await tester.pumpAndSettle();

      expect(
        controller.offset,
        greaterThanOrEqualTo(SnappingCards.itemExtent - 0.5),
      );
      expect(
        (controller.offset / SnappingCards.itemExtent).roundToDouble() *
            SnappingCards.itemExtent,
        closeTo(controller.offset, 0.5),
      );
    });
  });

  group('BareScrollView', () {
    testWidgets('scrolls a tall child and transforms hit testing', (
      WidgetTester tester,
    ) async {
      final ScrollController controller = ScrollController();
      addTearDown(controller.dispose);
      int? tappedRow;

      await tester.pumpWidget(
        Directionality(
          textDirection: TextDirection.ltr,
          child: Center(
            child: SizedBox(
              width: 300.0,
              height: 200.0,
              child: BareScrollView(
                controller: controller,
                child: Column(
                  children: <Widget>[
                    for (int i = 0; i < 10; i++)
                      GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTap: () => tappedRow = i,
                        child: SizedBox(
                          width: 300.0,
                          height: 50.0,
                          child: Text('Item $i'),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );

      expect(controller.position.maxScrollExtent, 300.0);

      // Scroll down 150px (three 50px items) after the 20px initial touch-slop step.
      await tester.drag(find.byType(BareScrollView), const Offset(0.0, -170.0));
      await tester.pumpAndSettle();
      expect(controller.offset, closeTo(150.0, 0.5));

      // Tapping near the top of the 200px viewport should hit item 3 (y = 150..200).
      final Offset topInside =
          tester.getTopLeft(find.byType(BareScrollView)) +
          const Offset(50.0, 25.0);
      await tester.tapAt(topInside);
      expect(tappedRow, 3);
    });
  });

  group('StickyHeader', () {
    testWidgets('scrolls until reaching the top edge, then pins in place', (
      WidgetTester tester,
    ) async {
      final ScrollController controller = ScrollController();
      addTearDown(controller.dispose);

      await tester.pumpWidget(
        Directionality(
          textDirection: TextDirection.ltr,
          child: SizedBox(
            width: 320.0,
            height: 400.0,
            child: StickyHeaderDemo(controller: controller),
          ),
        ),
      );

      // Initially sits below the 120px intro box.
      expect(tester.getTopLeft(find.text('Sticks')).dy, greaterThan(120.0));

      // Scroll 60px: header moves up by 60px.
      controller.jumpTo(60.0);
      await tester.pump();
      final double midY = tester.getTopLeft(find.text('Sticks')).dy;
      expect(midY, greaterThan(60.0));

      // Scroll past 120px: header pins at the top of the viewport (centered inside 56px box).
      controller.jumpTo(200.0);
      await tester.pump();
      final double pinnedY = tester.getTopLeft(find.text('Sticks')).dy;

      controller.jumpTo(500.0);
      await tester.pump();
      expect(tester.getTopLeft(find.text('Sticks')).dy, closeTo(pinnedY, 0.01));
      expect(pinnedY, lessThan(56.0));
    });
  });
}
