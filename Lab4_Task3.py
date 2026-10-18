"""
DS 170 / CMSC 170 - Laboratory Exercise No. 4
Task 3: A* on the 8-puzzle

Group I
    Senoy, Kyle Howard            <student number>
    Jomuad, Precious Mae E.       2023-00554
    Royo, Dave Christian          <student number>

This file is my part of the lab. It reads the two boards from a text file, keeps the
8-puzzle rules in one place, and hands those rules to the A* search that Lab4_Task2.py
already has, so the search is written once and the puzzle only supplies the moves.

Run it from the folder that holds the input files:

    python3 Lab4_Task3.py                          # reads sample_8_moves.txt
    python3 Lab4_Task3.py --file handout_board.txt
    python3 Lab4_Task3.py --heuristic misplaced
    python3 Lab4_Task3.py --compare

The board is a tuple of nine ints, read left to right and top to bottom, with 0 for
the blank. Lab4_Task2.py compares states with ==, so the two files have to agree on
this one form, and they do.
"""

import argparse
import time
import tracemalloc
from pathlib import Path

from Lab4_Task2 import astar, path_of

SIZE = 3
BLANK = 0
GOAL_A = (1, 2, 3, 4, 5, 6, 7, 8, BLANK)       # the goal board of the lab sheet

# key -> (label, row change, column change) for the empty block. The keys are the
# same ones Task 2 of Lab 3 used, so the moves read the same way in both labs.
MOVES = {
    'W': ('Up', -1, 0),
    'A': ('Left', 0, -1),
    'X': ('Down', 1, 0),
    'D': ('Right', 0, 1),
}


# ------------------------------------------------------------------ board checks
def is_valid_state(state):
    """True iff state is nine ints holding the tiles 1-8 once each and one blank."""
    return (isinstance(state, tuple) and len(state) == SIZE * SIZE
            and all(isinstance(tile, int) for tile in state)
            and sorted(state) == list(range(SIZE * SIZE)))


def inversions(state):
    """Pairs of tiles that are in the wrong order, the blank left out."""
    tiles = [tile for tile in state if tile != BLANK]
    return sum(1 for i in range(len(tiles)) for j in range(i + 1, len(tiles))
               if tiles[i] > tiles[j])


def is_solvable(initial, goal):
    """On a 3x3 board a board reaches the goal iff both have the same parity.

    Every legal move changes the number of inversions by an even amount, so half the
    boards cannot reach a given goal at all. I check that before searching, because
    otherwise A* walks the whole reachable half and then reports nothing.
    """
    return inversions(initial) % 2 == inversions(goal) % 2


# ------------------------------------------------------------------- file input
def read_boards(path):
    """Read the initial and goal boards from `path` and return them as two tuples.

    The format is the lab sheet's: three rows of three comma-separated numbers for the
    initial board, then three rows for the goal board. Blank lines are skipped, and a
    label line like "Initial State" is skipped too. Anything else has to be a board row.
    """
    try:
        text = Path(path).read_text()
    except OSError as error:
        raise ValueError(f"cannot open {path}: {error.strerror or error}") from None

    rows = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        # A label such as "Initial State" has no digits, so it is not a board row.
        if not line or line.startswith("#") or not any(ch.isdigit() for ch in line):
            continue
        rows.append((number, line))

    if len(rows) != 2 * SIZE:
        raise ValueError(f"{path}: {len(rows)} board rows, but the file needs "
                         f"{2 * SIZE} (three for each board)")

    initial = parse_board([line for _, line in rows[:SIZE]], path, "initial board", rows[0][0])
    goal = parse_board([line for _, line in rows[SIZE:]], path, "goal board", rows[SIZE][0])
    return initial, goal


def parse_board(rows, path, which, first_line):
    """Turn three text rows into a board tuple, or raise ValueError naming the fault."""
    state = []
    for offset, row in enumerate(rows):
        cells = [cell.strip() for cell in row.split(",")]
        if len(cells) != SIZE:
            raise ValueError(f"{path}, line {first_line + offset}: the {which} row has "
                             f"{len(cells)} numbers, need {SIZE}")
        for cell in cells:
            if not cell.isdigit():
                raise ValueError(f"{path}, line {first_line + offset}: {cell!r} is not a "
                                 f"tile number (use 0 for the blank)")
            state.append(int(cell))

    state = tuple(state)
    repeated = sorted({tile for tile in state if state.count(tile) > 1})
    missing = [tile for tile in range(SIZE * SIZE) if tile not in state]
    if repeated or missing:
        faults = []
        if repeated:
            faults.append("repeated " + ", ".join(map(str, repeated)))
        if missing:
            faults.append("missing " + ", ".join(map(str, missing)))
        raise ValueError(f"{path}, the {which}: the tiles 0-8 must each appear once "
                         f"({'; '.join(faults)})")
    return state


# ----------------------------------------------------------------------- moves
def get_possible_moves(state):
    """Return {key: new_state} for every legal move of the empty block.

    The board is a flat tuple, so a move is a swap between the blank's index and the
    index one row or one column away. Off the board means the move is not legal.
    """
    blank = state.index(BLANK)
    row, col = divmod(blank, SIZE)
    result = {}
    for key, (_, row_step, col_step) in MOVES.items():
        new_row, new_col = row + row_step, col + col_step
        if 0 <= new_row < SIZE and 0 <= new_col < SIZE:
            target = new_row * SIZE + new_col
            tiles = list(state)
            tiles[blank], tiles[target] = tiles[target], tiles[blank]
            result[key] = tuple(tiles)
    return result


def validate_move(state, key):
    """True iff `key` is a known move and that move is legal from `state`."""
    return key in MOVES and key in get_possible_moves(state)


def successors(state):
    """The move list in the shape astar() wants: (action, next_state, step_cost)."""
    return [(key, new_state, 1) for key, new_state in get_possible_moves(state).items()]


# ------------------------------------------------------------------ heuristics
def manhattan(state, goal):
    """Sum of the row and column distances each tile still has to travel.

    A move shifts one tile by one cell, so no solution can be shorter than this sum.
    That makes it admissible, and A* then returns a shortest solution.
    """
    home = {tile: index for index, tile in enumerate(goal)}
    total = 0
    for index, tile in enumerate(state):
        if tile == BLANK:
            continue
        row, col = divmod(index, SIZE)
        goal_row, goal_col = divmod(home[tile], SIZE)
        total += abs(row - goal_row) + abs(col - goal_col)
    return total


def misplaced(state, goal):
    """How many tiles are not on their goal cell. The blank is not counted."""
    return sum(1 for tile, wanted in zip(state, goal) if tile != wanted and tile != BLANK)


HEURISTICS = {
    "manhattan": (manhattan, "Manhattan distance"),
    "misplaced": (misplaced, "misplaced tiles"),
}


# ------------------------------------------------------------------- searching
def solve(initial, goal, heuristic_name="manhattan"):
    """Run A* and print the board at every level, plus the run's counts.

    Returns a dict of the numbers the report quotes, so the caller does not have to
    read them off the screen.
    """
    heuristic, label = HEURISTICS[heuristic_name]
    print(f"Heuristic: {label}")

    if not is_solvable(initial, goal):
        print(f"\nNo solution. The initial board has {inversions(initial)} inversions and "
              f"the goal has {inversions(goal)}.")
        print("Both counts have to have the same parity, and on this board they do not.")
        return {"solved": False, "moves": None, "expanded": 0, "generated": 0}

    # A* asks the heuristic once for the start node and once for every node it makes,
    # so counting the calls counts the nodes generated.
    calls = {"generated": 0}

    def counted(state, goal_state):
        calls["generated"] += 1
        return heuristic(state, goal_state)

    tracemalloc.start()
    started = time.perf_counter()
    goal_node, expanded = astar(initial, goal, successors, counted)
    elapsed = time.perf_counter() - started
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    if goal_node is None:
        print("\nA* found no route to the goal.")
        return {"solved": False, "moves": None, "expanded": expanded,
                "generated": calls["generated"]}

    print_levels(goal_node)
    print(f"\nTotal number of moves to reach the goal state = {goal_node.g_cost}")
    print(f"States expanded by A* = {expanded}")
    print(f"Nodes generated = {calls['generated']}")
    print(f"Time = {elapsed:.4f} s")
    print(f"Peak memory = {peak / 1024:.1f} KB")

    return {"solved": True, "moves": goal_node.g_cost, "expanded": expanded,
            "generated": calls["generated"], "seconds": elapsed, "peak": peak,
            "sequence": move_sequence(goal_node)}


def print_levels(goal_node):
    """Print every board from the start to the goal, one level at a time."""
    nodes = path_of(goal_node)
    for level, node in enumerate(nodes):
        if level == 0:
            print("\nRoot Node (Level 0)")
        else:
            print(f"\nLevel {level}  (blank moved {MOVES[node.action][0]})")
        for line in board_lines(node.state):
            print(line)


def move_sequence(goal_node):
    """The move keys from the root to the goal, e.g. 'A A W D'."""
    return [node.action for node in path_of(goal_node)[1:]]


def compare(initial, goal):
    """Run both heuristics on the same pair of boards and print the counts side by side."""
    results = [(label, solve_quiet(initial, goal, name))
               for name, (_, label) in HEURISTICS.items()]
    print(f"{'Heuristic':<22}{'Moves':>6}{'Expanded':>10}{'Generated':>11}{'Time':>10}")
    for label, counts in results:
        print(f"{label:<22}{counts['moves']!s:>6}{counts['expanded']:>10}"
              f"{counts['generated']:>11}{counts['seconds']:>9.4f}s")


def solve_quiet(initial, goal, heuristic_name):
    """The same search without the level-by-level printout, for the comparison table."""
    heuristic = HEURISTICS[heuristic_name][0]
    if not is_solvable(initial, goal):
        return {"solved": False, "moves": "none", "expanded": 0, "generated": 0, "seconds": 0.0}
    calls = {"generated": 0}

    def counted(state, goal_state):
        calls["generated"] += 1
        return heuristic(state, goal_state)

    started = time.perf_counter()
    goal_node, expanded = astar(initial, goal, successors, counted)
    elapsed = time.perf_counter() - started
    return {"solved": goal_node is not None,
            "moves": goal_node.g_cost if goal_node else "none",
            "expanded": expanded, "generated": calls["generated"], "seconds": elapsed}


# ---------------------------------------------------------------------- output
def board_lines(state):
    """The board as three text rows, the blank as a space."""
    return ["  " + " ".join(" " if tile == BLANK else str(tile)
                            for tile in state[row * SIZE:(row + 1) * SIZE])
            for row in range(SIZE)]


def board_box(state):
    """The board in a box, for the two boards the file gave."""
    lines = ["+---+---+---+"]
    for row in range(SIZE):
        tiles = state[row * SIZE:(row + 1) * SIZE]
        lines.append("| " + " | ".join(" " if tile == BLANK else str(tile) for tile in tiles) + " |")
        lines.append("+---+---+---+")
    return lines


def print_boards(initial, goal, source="a file"):
    """The starting picture: the two boards the search works from."""
    print(f"Initial state (from {source})")
    print("\n".join(board_box(initial)))
    print("Goal state")
    print("\n".join(board_box(goal)))
    print()


# ------------------------------------------------------------------------- CLI
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Solve the 8-puzzle with A*, reading both boards from a file.")
    parser.add_argument("--file", default="sample_8_moves.txt",
                        help="input file with the initial and goal boards "
                             "(default: sample_8_moves.txt)")
    parser.add_argument("--heuristic", choices=sorted(HEURISTICS), default="manhattan",
                        help="which heuristic A* uses (default: manhattan)")
    parser.add_argument("--compare", action="store_true",
                        help="run both heuristics on the same boards")
    args = parser.parse_args(argv)

    print("DS 170 / CMSC 170 - Laboratory Exercise No. 4")
    print("8-puzzle with A*\n")

    try:
        initial, goal = read_boards(args.file)
    except ValueError as error:
        print(f"Input error: {error}")
        return 2

    print_boards(initial, goal, args.file)
    if args.compare:
        compare(initial, goal)
    else:
        solve(initial, goal, args.heuristic)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
