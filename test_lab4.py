"""Check battery for Lab 4. Not part of the submission.

Runs the two program files the way the marker's runs do: parses the input files,
plays the moves, searches with A*, and compares A*'s answer against a plain
breadth-first search written here, so "A* returns the shortest solution" is measured
and not assumed. The merged submission file is checked as well, because that is the
file being marked.

    python3 test_lab4.py
"""

import pathlib
import random
import unittest
from collections import deque

import Lab4_Task2
import Lab4_Task3 as task3

HERE = pathlib.Path(__file__).resolve().parent
GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)
SAMPLE = (1, 5, 2, 7, 4, 3, 8, 6, 0)


def bfs_depth(initial, goal):
    """Shortest number of moves between two boards, the reference A* has to match."""
    if task3.inversions(initial) % 2 != task3.inversions(goal) % 2:
        return None
    seen = {initial: 0}
    queue = deque([initial])
    while queue:
        state = queue.popleft()
        if state == goal:
            return seen[state]
        for new_state in task3.get_possible_moves(state).values():
            if new_state not in seen:
                seen[new_state] = seen[state] + 1
                queue.append(new_state)
    return None


def random_board(steps=40, seed=None):
    """A solvable board, made by walking random legal moves away from the goal."""
    rng = random.Random(seed)
    state, previous = GOAL, None
    undo = {'W': 'X', 'X': 'W', 'A': 'D', 'D': 'A'}
    for _ in range(steps):
        options = task3.get_possible_moves(state)
        keys = [key for key in options if key != previous] or list(options)
        key = rng.choice(keys)
        state, previous = options[key], undo[key]
    return state


class InputTests(unittest.TestCase):
    def test_sample_file(self):
        self.assertEqual(task3.read_boards(HERE / "sample_8_moves.txt"), (SAMPLE, GOAL))

    def test_label_lines_are_skipped(self):
        """The handout prints "Initial State" above each block, so the reader allows it."""
        self.assertEqual(task3.read_boards(HERE / "handout_board.txt"),
                         ((1, 2, 3, 8, 0, 4, 7, 6, 5), GOAL))

    def test_duplicate_tile_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            task3.read_boards(HERE / "invalid_duplicate.txt")
        self.assertIn("repeated 1", str(caught.exception))
        self.assertIn("missing 2", str(caught.exception))

    def test_short_row_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            task3.read_boards(HERE / "invalid_row.txt")
        self.assertIn("2 numbers, need 3", str(caught.exception))

    def test_non_number_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            task3.read_boards(HERE / "invalid_number.txt")
        self.assertIn("'x' is not a tile number", str(caught.exception))

    def test_missing_goal_board_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            task3.read_boards(HERE / "missing_goal.txt")
        self.assertIn("3 board rows", str(caught.exception))

    def test_missing_file_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            task3.read_boards(HERE / "no_such_file.txt")
        self.assertIn("cannot open", str(caught.exception))


class MoveTests(unittest.TestCase):
    def test_corner_has_two_moves_and_centre_has_four(self):
        self.assertEqual(len(task3.get_possible_moves((0, 1, 2, 3, 4, 5, 6, 7, 8))), 2)
        self.assertEqual(len(task3.get_possible_moves((1, 2, 3, 4, 0, 5, 6, 7, 8))), 4)

    def test_every_move_is_reversible(self):
        state = random_board(steps=12, seed=3)
        for key, new_state in task3.get_possible_moves(state).items():
            back = {'W': 'X', 'X': 'W', 'A': 'D', 'D': 'A'}[key]
            self.assertEqual(task3.get_possible_moves(new_state)[back], state)

    def test_moves_keep_the_board_valid(self):
        for _ in range(30):
            state = random_board(steps=20, seed=random.random())
            for new_state in task3.get_possible_moves(state).values():
                self.assertTrue(task3.is_valid_state(new_state))

    def test_validate_move_refuses_impossible_keys(self):
        corner = (0, 1, 2, 3, 4, 5, 6, 7, 8)
        self.assertFalse(task3.validate_move(corner, 'W'))     # blank on the top row
        self.assertFalse(task3.validate_move(corner, 'A'))     # blank in the left column
        self.assertFalse(task3.validate_move(corner, 'Q'))     # not a move at all
        self.assertTrue(task3.validate_move(corner, 'X'))


class HeuristicTests(unittest.TestCase):
    def test_goal_has_zero_distance(self):
        self.assertEqual(task3.manhattan(GOAL, GOAL), 0)
        self.assertEqual(task3.misplaced(GOAL, GOAL), 0)

    def test_manhattan_is_admissible(self):
        """It must never claim more moves than the board really needs."""
        for seed in range(40):
            state = random_board(steps=24, seed=seed)
            self.assertLessEqual(task3.manhattan(state, GOAL), bfs_depth(state, GOAL))

    def test_manhattan_dominates_misplaced(self):
        for seed in range(40):
            state = random_board(steps=24, seed=seed)
            self.assertGreaterEqual(task3.manhattan(state, GOAL), task3.misplaced(state, GOAL))


class SearchTests(unittest.TestCase):
    def test_astar_matches_bfs_on_the_sample_board(self):
        node, expanded = Lab4_Task2.astar(SAMPLE, GOAL, task3.successors, task3.manhattan)
        self.assertIsNotNone(node)
        self.assertEqual(node.g_cost, 8)
        self.assertEqual(node.g_cost, bfs_depth(SAMPLE, GOAL))

    def test_astar_is_optimal_on_forty_boards(self):
        for seed in range(40):
            state = random_board(steps=22, seed=seed)
            node, _ = Lab4_Task2.astar(state, GOAL, task3.successors, task3.manhattan)
            self.assertEqual(node.g_cost, bfs_depth(state, GOAL), f"seed {seed}")

    def test_misplaced_is_admissible_too(self):
        for seed in range(20):
            state = random_board(steps=22, seed=seed)
            node, _ = Lab4_Task2.astar(state, GOAL, task3.successors, task3.misplaced)
            self.assertEqual(node.g_cost, bfs_depth(state, GOAL), f"seed {seed}")

    def test_already_solved_board_costs_nothing(self):
        node, expanded = Lab4_Task2.astar(GOAL, GOAL, task3.successors, task3.manhattan)
        self.assertEqual(node.g_cost, 0)
        self.assertEqual(expanded, 0)

    def test_handout_board_cannot_reach_its_goal(self):
        """1,2,3 / 8,0,4 / 7,6,5 has 7 inversions against the goal's 0, so it is impossible."""
        handout = (1, 2, 3, 8, 0, 4, 7, 6, 5)
        self.assertFalse(task3.is_solvable(handout, GOAL))
        self.assertIsNone(bfs_depth(handout, GOAL))

    def test_solve_reports_no_solution_for_an_impossible_board(self):
        counts = task3.solve((2, 1, 3, 4, 5, 6, 7, 8, 0), GOAL)
        self.assertFalse(counts["solved"])

    def test_more_states_expanded_never_beats_the_count_generated(self):
        counts = task3.solve_quiet(SAMPLE, GOAL, "manhattan")
        self.assertGreaterEqual(counts["generated"], counts["expanded"])


class MergedFileTests(unittest.TestCase):
    """The merged file is what gets submitted, so it is tested on its own terms."""

    @classmethod
    def setUpClass(cls):
        try:
            import CMSC170_Lab4_AStar_8Puzzle as merged
        except ImportError:
            raise unittest.SkipTest("merged file not built yet")
        cls.merged = merged

    def test_merged_file_solves_the_sample(self):
        node, expanded = self.merged.astar(SAMPLE, GOAL, self.merged.successors,
                                           self.merged.manhattan)
        self.assertEqual(node.g_cost, 8)
        self.assertEqual(expanded, 8)

    def test_merged_file_reads_the_same_boards(self):
        self.assertEqual(self.merged.read_boards(HERE / "sample_8_moves.txt"), (SAMPLE, GOAL))

    def test_merged_file_keeps_one_copy_of_the_rules(self):
        text = (HERE / "CMSC170_Lab4_AStar_8Puzzle.py").read_text()
        for name in ("def get_possible_moves", "def is_solvable", "def manhattan", "class Node"):
            self.assertEqual(text.count(name), 1, name)

    def test_merged_file_has_the_graph_demo_from_task_2(self):
        node, _ = self.merged.astar("S", "G", self.merged.graph_successors,
                                    self.merged.graph_heuristic)
        self.assertEqual(node.g_cost, 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
