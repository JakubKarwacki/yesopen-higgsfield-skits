"""Routing regressions independent of ComfyUI and GPU dependencies."""
import itertools
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from graph_layout import best_order, crossings, lane_items, lane_paths, drawn_pieces, overlaps, simplify, build_reroutes, _crosses_box


class LaneOrderingTests(unittest.TestCase):
    def test_clear_branch_can_leave_trunk_needed_by_other_branch(self):
        src = (1, 0)
        paths = {1: (src, [(100, -100)]), 2: (src, [(100, -100)])}
        ends = {1: ((0, 0), (400, 100)), 2: ((0, 0), (500, -200))}
        boxes = [(200, -80, 280, -20)]
        simplify(paths, ends, boxes)
        self.assertEqual(paths[1][1], [])
        self.assertEqual(paths[2][1], [(100, -100)])
        self.assertTrue(all(not _crosses_box(a, b, boxes)
                            for _, _, a, b in drawn_pieces(paths, ends)))

    def test_horizontal_bus_needs_no_waypoint_even_with_different_midpoints(self):
        src = (1, 0)
        paths = {1: (src, [(100, 0)]), 2: (src, [(100, 0)])}
        ends = {1: ((0, 0), (200, 0)), 2: ((0, 0), (300, 0))}
        self.assertEqual(simplify(paths, ends, []), 2)
        self.assertEqual(paths, {1: (src, []), 2: (src, [])})
        self.assertEqual(build_reroutes(paths)[0], [])

    def test_bus_shortens_together_without_crossing_obstacle(self):
        src = (1, 0)
        paths = {1: (src, [(60, -40), (340, -40)]),
                 2: (src, [(60, -40), (340, -40)])}
        ends = {1: ((0, 0), (400, 100)), 2: ((0, 0), (500, 150))}
        boxes = [(100, 20, 300, 80)]
        self.assertGreater(simplify(paths, ends, boxes), 0)
        self.assertEqual(paths[1][1], paths[2][1])
        self.assertEqual(len(paths[1][1]), 1)
        self.assertEqual(len(build_reroutes(paths)[0]), 1)
        self.assertTrue(all(not _crosses_box(a, b, boxes)
                            for _, _, a, b in drawn_pieces(paths, ends)))

    def test_exact_order_matches_exhaustive_search(self):
        rng = random.Random(42)
        for n in range(8):
            for _ in range(3):
                items = [(rng.randrange(8) * 10, tuple(rng.randrange(8) * 10
                          for _ in range(rng.randrange(1, 4))), i) for i in range(n)]
                expected = min(itertools.permutations(items),
                               key=lambda o: (crossings(o), [it[0] for it in o]))
                actual = best_order(items)
                self.assertEqual(crossings(actual), crossings(expected))
                self.assertEqual([it[0] for it in actual], [it[0] for it in expected])
                self.assertEqual(sorted(it[2] for it in actual), list(range(n)))

    def test_medium_corridor_is_exact_and_deterministic(self):
        items = [(i * 20, (i * 20 + 10,), i) for i in range(12)]
        actual = best_order(items)
        self.assertEqual(crossings(actual), 0)
        self.assertEqual(actual, best_order(items))

    def test_large_corridor_reaches_insertion_local_minimum(self):
        rng = random.Random(7)
        items = [(rng.randrange(100), (rng.randrange(100), rng.randrange(100)), i)
                 for i in range(16)]
        actual = best_order(items)
        score = crossings(actual)
        self.assertEqual(sorted(it[2] for it in actual), list(range(16)))
        self.assertEqual(actual, best_order(items))
        for i in range(len(actual)):
            for j in range(len(actual)):
                candidate = actual[:]
                candidate.insert(j, candidate.pop(i))
                self.assertGreaterEqual(crossings(candidate), score)

    def test_separate_sources_do_not_share_vertical_lane(self):
        specs = [(1, (1, 0), 0, 100, 0, 1, 0),
                 (2, (2, 0), 20, 120, 0, 1, 0)]
        ends = {1: ((100, 0), (300, 100)), 2: ((100, 20), (300, 120))}
        items, channels = lane_items(specs, lambda _, i: -40 - 22 * i)
        paths = lane_paths(specs, items, channels, {0: (100, 300)},
                           {lid: (a[0], b[0]) for lid, (a, b) in ends.items()})
        self.assertEqual(overlaps(drawn_pieces(paths, ends)), [])


if __name__ == "__main__":
    unittest.main()
