"""
DS 170 / CMSC 170 - Laboratory Exercise No. 4
A* Algorithm in Python, applied to the 8-puzzle

Group I
    Senoy, Kyle Howard            <student number>
    Jomuad, Precious Mae E.       2023-00554
    Royo, Dave Christian          <student number>

This is the group's single program for the lab. It has three parts:

    Part 1  the A* search (Task 2): the Node class, the open and closed lists, and a
            small weighted graph that shows the search running
    Part 2  the 8-puzzle (Task 3): the file reader, the state checks, the move
            generator, the two heuristics and the level-by-level printout
    Part 3  the window: play the puzzle, then watch A* solve it
    Part 4  the menu that starts any of the three

Run it from the folder that holds the input files:

    python3 CMSC170_Lab4_AStar_8Puzzle.py

The menu asks how to run the program and which task to run. The window needs a desktop
session; the terminal path does not. The parts are joined from the members' own files,
and every rule is defined once, so the window, the search and the file reader cannot
disagree about what a legal move is. A board is a tuple of nine ints with 0 for the
blank everywhere in the file.
"""

import heapq
import itertools
import sys
import time
import tracemalloc
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog


# ==============================================================================
# PART 1 - Task 2: the A* search
# ==============================================================================

# ------------------------------------------------------------------ Node class
class Node:
    """One node in the A* search tree.

    f_cost = g_cost + h_cost
      g_cost: real cost paid from the initial state to this node
      h_cost: heuristic estimate of the cost from this node to the goal
      f_cost: estimated cost of the cheapest solution that goes through this node
    """

    def __init__(self, state, parent=None, action=None, g_cost=0, h_cost=0):
        self.state = state
        self.parent = parent        # Node we came from (None for the root)
        self.action = action        # action that produced this node
        self.g_cost = g_cost
        self.h_cost = h_cost
        self.f_cost = g_cost + h_cost

    def __repr__(self):
        return (f"Node(state={self.state}, g={self.g_cost}, "
                f"h={self.h_cost}, f={self.f_cost})")


def path_of(node):
    """Walk parent pointers from `node` back to the root; return root -> node."""
    nodes = []
    while node is not None:
        nodes.append(node)
        node = node.parent
    return nodes[::-1]


# ------------------------------------------------------------------- A* search
def astar(initial_state, goal_state, get_successors, heuristic, verbose=False):
    """A* search.

    OPEN list  : a priority queue (min-heap) of nodes waiting to be expanded,
                 ordered by f_cost. Ties are broken by the smaller h_cost
                 (closer to the goal), then by insertion order.
    CLOSED list: the states already expanded, with the best g_cost they were
                 expanded with.
    best_g     : cheapest g_cost found so far for every state that was generated.
                 If a cheaper route to a state appears, a new node replaces the old
                 one, so the result stays optimal when the heuristic is admissible.
                 Stale heap entries are skipped when they are popped.

    Returns (goal_node, nodes_expanded); goal_node is None if no path exists.
    """
    counter = itertools.count()            # unique tie-breaker so Nodes are never compared
    root = Node(initial_state, g_cost=0, h_cost=heuristic(initial_state, goal_state))

    open_list = [(root.f_cost, root.h_cost, next(counter), root)]
    best_g = {initial_state: 0}
    closed = {}                            # state -> g_cost when expanded
    expanded = 0

    while open_list:
        _, _, _, node = heapq.heappop(open_list)      # lowest f_cost node

        if node.g_cost > best_g.get(node.state, float("inf")):
            continue                                  # stale entry: a cheaper route exists
        if node.state in closed and closed[node.state] <= node.g_cost:
            continue                                  # already expanded at least as cheaply

        if node.state == goal_state:                  # goal test when EXPANDED (keeps A* optimal)
            return node, expanded

        closed[node.state] = node.g_cost
        expanded += 1
        if verbose:
            print(f"expand {node.state}  g={node.g_cost} h={node.h_cost} f={node.f_cost}")

        for action, next_state, step_cost in get_successors(node.state):
            g = node.g_cost + step_cost
            if g >= best_g.get(next_state, float("inf")):
                continue                              # not a better route to next_state
            best_g[next_state] = g
            child = Node(next_state, node, action, g, heuristic(next_state, goal_state))
            heapq.heappush(open_list, (child.f_cost, child.h_cost, next(counter), child))

    return None, expanded


# ---------------------------------------------------------------------- output
def print_path(goal_node, show_state=str):
    """Print every node from the root to the goal and the total cost."""
    if goal_node is None:
        print("No path to the goal exists.")
        return
    for i, node in enumerate(path_of(goal_node)):
        label = "Start" if i == 0 else f"Step {i} (action {node.action})"
        print(f"{label}: {show_state(node.state)}   "
              f"g={node.g_cost} h={node.h_cost} f={node.f_cost}")
    print(f"Total cost = {goal_node.g_cost}")


# ------------------------------------------------------------------------ demo
# state_space is the graph itself: {state: [(action, next_state, step_cost), ...]}
state_space = {
    "S": [("S->A", "A", 1), ("S->B", "B", 4)],
    "A": [("A->B", "B", 2), ("A->C", "C", 5), ("A->D", "D", 12)],
    "B": [("B->C", "C", 2)],
    "C": [("C->G", "G", 3)],
    "D": [("D->G", "G", 3)],
    "G": [],
}
# Admissible heuristic: never larger than the true remaining cost.
h_table = {"S": 7, "A": 6, "B": 4, "C": 3, "D": 3, "G": 0}


def graph_successors(state):
    return state_space[state]


def graph_heuristic(state, goal):
    return h_table[state]

# ==============================================================================
# PART 2 - Task 3: the 8-puzzle, read from a file
# ==============================================================================

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


# ==============================================================================
# PART 3 - the window, where the puzzle and the search work together
# ==============================================================================

STEP_MS = 600                    # how long one A* move stays on screen
DEFAULT_FILE = "sample_8_moves.txt"

# Which tile moves when a tile next to the blank is clicked. The key names the
# direction the blank moves, because that is what the sheet's keys mean.
CLICK_KEYS = {1: 'D', -1: 'A', -3: 'W', 3: 'X'}
UNDO = {'W': 'X', 'X': 'W', 'A': 'D', 'D': 'A'}

# ------------------------------------------------------------------ look of the app
# Tk only sees the fonts fontconfig exposes to it, so the first family from this list
# that Tk really has is used for everything.
UI_FONT_CHOICES = ("Liberation Sans", "Nimbus Sans L", "DejaVu Sans", "Helvetica", "Arial")
FALLBACK_FONT = "TkDefaultFont"

INK = "#1f2933"
MUTED = "#6b7280"
BG = "#f4f5f7"
CARD = "#ffffff"
LINE = "#e3e6ea"
TILE = "#ffffff"
TILE_EDGE = "#e4e8ed"
TILE_HOVER = "#eef4ff"
TILE_MOVED = "#3b82f6"
TILE_INK_MOVED = "#ffffff"
HOLE = "#e9ecf0"
PRIMARY = "#23272f"
PRIMARY_HOVER = "#3a4048"
GHOST = "#e9ecf1"
GHOST_HOVER = "#dde2e9"
OK = "#1a7f37"
BAD = "#b42318"

TILE_SIZE = 92
TILE_GAP = 10
BOARD_PAD = 14

HERE = Path(__file__).resolve().parent


def pick_font(preferred, fallback=FALLBACK_FONT):
    """The first font family in `preferred` that Tk can actually use."""
    available = {name.lower() for name in tkfont.families()}
    for name in preferred:
        if name.lower() in available:
            return name
    return fallback


def rounded_box(canvas, x1, y1, x2, y2, radius, **options):
    """A rounded rectangle. Tkinter has none, so the outline is a smoothed polygon."""
    points = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
              x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
              x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
    return canvas.create_polygon(points, smooth=True, **options)


class PuzzleGUI:
    """The window. The game and replay state live here so the checks can drive it."""

    def __init__(self, root, mode="play"):
        self.root = root
        self.mode = mode
        self.initial = GOAL_A
        self.goal = GOAL_A
        self.board = GOAL_A
        self.source = "the goal board"
        self.player_moves = []
        self.solution_nodes = None       # the A* answer for this start board
        self.solution_moves = []
        self.replay_index = 0
        self.replay_job = None
        self.solved = False
        self.gave_up = False
        self.heuristic_name = "manhattan"

        root.title("8-Puzzle with A*")
        root.configure(bg=BG)
        root.resizable(False, False)
        self.ui_font = pick_font(UI_FONT_CHOICES)

        self._build_widgets()
        self._bind_keys()
        self.new_board(GOAL_A, "the goal board")
        self.set_mode(mode)
        root.geometry("+30+20")

    # ------------------------------------------------------------------ widgets
    def _build_widgets(self):
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=26, pady=(16, 0))
        tk.Label(head, text="8-Puzzle with A*", font=(self.ui_font, 22, "bold"),
                 bg=BG, fg=INK).pack(anchor="w")
        self.subtitle = tk.Label(head, text="", font=(self.ui_font, 11), bg=BG, fg=MUTED)
        self.subtitle.pack(anchor="w")

        toggle = tk.Frame(head, bg=BG)
        toggle.pack(anchor="w", pady=(10, 0))
        self.mode_buttons = {}
        for key, text in (("play", "Play it yourself"), ("solve", "Let A* solve it")):
            button = self._button(toggle, text, lambda chosen=key: self.set_mode(chosen),
                                  kind="primary")
            button.pack(side="left", padx=(0, 8))
            self.mode_buttons[key] = button

        tools = tk.Frame(self.root, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        tools.pack(fill="x", padx=26, pady=(14, 0))
        self.source_label = tk.Label(tools, text="", font=(self.ui_font, 9), bg=CARD, fg=MUTED,
                                     anchor="w")
        self.source_label.pack(fill="x", padx=14, pady=(10, 0))
        row = tk.Frame(tools, bg=CARD)
        row.pack(fill="x", padx=14, pady=(6, 12))
        self.load_button = self._button(row, "Load from file", self.load_from_file, kind="ghost")
        self.load_button.pack(side="left")
        self.random_button = self._button(row, "Random board", self.random_board, kind="ghost")
        self.random_button.pack(side="left", padx=8)
        self.heuristic_button = self._button(row, "Heuristic: Manhattan", self.switch_heuristic,
                                             kind="ghost")
        self.heuristic_button.pack(side="right")

        side = 3 * TILE_SIZE + 2 * TILE_GAP + 2 * BOARD_PAD
        self.board_canvas = tk.Canvas(self.root, width=side, height=side, bg=BG,
                                      highlightthickness=0, cursor="arrow")
        self.board_canvas.pack(pady=(14, 4))
        self.board_canvas.bind("<Button-1>", self.on_board_click)
        self.board_canvas.bind("<Motion>", self.on_board_hover)
        self.cell_boxes = []
        self.tile_shapes = []
        self.tile_labels = []
        for index in range(9):
            row_index, col = divmod(index, 3)
            x1 = BOARD_PAD + col * (TILE_SIZE + TILE_GAP)
            y1 = BOARD_PAD + row_index * (TILE_SIZE + TILE_GAP)
            self.cell_boxes.append((x1, y1, x1 + TILE_SIZE, y1 + TILE_SIZE))
            rounded_box(self.board_canvas, x1, y1 + 3, x1 + TILE_SIZE, y1 + TILE_SIZE + 3,
                        18, fill="#e8ebef", outline="")                     # soft shadow
            shape = rounded_box(self.board_canvas, x1, y1, x1 + TILE_SIZE, y1 + TILE_SIZE,
                                18, fill=TILE, outline=TILE_EDGE, width=1)
            label = self.board_canvas.create_text(x1 + TILE_SIZE / 2, y1 + TILE_SIZE / 2 - 2,
                                                  text="", font=(self.ui_font, 30, "bold"),
                                                  fill=INK)
            self.tile_shapes.append(shape)
            self.tile_labels.append(label)

        status_row = tk.Frame(self.root, bg=BG)
        status_row.pack(fill="x", padx=26, pady=(6, 0))
        self.status_accent = tk.Frame(status_row, bg=LINE, width=3, height=36)
        self.status_accent.pack(side="left", fill="y", padx=(0, 10))
        self.status = tk.Label(status_row, text="", bg=BG, fg=INK,
                               font=(self.ui_font, 11, "bold"), wraplength=470,
                               justify="left", anchor="w")
        self.status.pack(side="left", fill="x", expand=True)

        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="x", padx=26, pady=(12, 0))
        self.solve_button = self._button(row, "Solve with A*", self.show_solution, kind="primary")
        self.solve_button.pack(side="left")
        self.stop_button = self._button(row, "Stop", self.stop_replay, kind="ghost",
                                        state="disabled")
        self.stop_button.pack(side="left", padx=8)
        self.reset_button = self._button(row, "Back to the start board", self.reset_board,
                                         kind="ghost")
        self.reset_button.pack(side="right")

        log_card = tk.Frame(self.root, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        log_card.pack(fill="x", padx=26, pady=(12, 16))
        tk.Label(log_card, text="A* LOG", font=(self.ui_font, 8, "bold"), bg=CARD,
                 fg=MUTED).pack(anchor="w", padx=14, pady=(10, 0))
        self.log = tk.Text(log_card, height=5, font=(self.ui_font, 9), bg=CARD, fg=INK,
                           relief="flat", highlightthickness=0, borderwidth=0, wrap="word",
                           state="disabled")
        self.log.pack(fill="both", expand=True, padx=14, pady=(4, 12))

    def _button(self, parent, text, command, kind="ghost", state="normal"):
        background, foreground, hover = {"primary": (PRIMARY, "#ffffff", PRIMARY_HOVER),
                                         "ghost": (GHOST, INK, GHOST_HOVER)}[kind]
        button = tk.Button(parent, text=text, command=command, font=(self.ui_font, 10, "bold"),
                           bg=background, fg=foreground, activebackground=hover,
                           activeforeground=foreground, relief="flat", borderwidth=0,
                           padx=14, pady=7, cursor="hand2", state=state)
        return button

    def _bind_keys(self):
        for key in MOVES:
            self.root.bind(key.lower(), lambda event, chosen=key: self.play(chosen))
        for event_name, key in (("<Up>", 'W'), ("<Left>", 'A'), ("<Down>", 'X'), ("<Right>", 'D')):
            self.root.bind(event_name, lambda event, chosen=key: self.play(chosen))

    # ----------------------------------------------------------------- modes
    def default_status(self):
        """The line the window falls back to when nothing else needs saying."""
        if not is_solvable(self.board, self.goal):
            return (f"This board cannot reach the goal: {inversions(self.board)} inversions "
                    f"against {inversions(self.goal)}.", BAD)
        if self.solved and self.player_moves:
            return "Solved it yourself. A* can still show its own answer.", OK
        if self.mode == "solve":
            return "Press 'Solve with A*' to watch the search work.", INK
        return "Click a tile next to the empty space, or use W A X D.", INK

    def set_mode(self, mode):
        """Two modes, one window. The search is the point in "solve" mode."""
        self.mode = mode
        self.subtitle.config(text="Task 3: A* on the 8-puzzle, played or solved"
                             if mode == "play" else
                             "Task 3: A* searching the board in this window")
        for key, button in self.mode_buttons.items():
            button.config(bg=PRIMARY if key == mode else GHOST,
                          fg="#ffffff" if key == mode else INK)
        self.set_status(*self.default_status())

    def switch_heuristic(self):
        """Swap between the two heuristics and throw away the old answer."""
        self.heuristic_name = "misplaced" if self.heuristic_name == "manhattan" else "manhattan"
        self.heuristic_button.config(text=f"Heuristic: {HEURISTICS[self.heuristic_name][1].title()}")
        self.solution_nodes = None
        self.set_status(f"Now using {HEURISTICS[self.heuristic_name][1]}.", MUTED)

    # ------------------------------------------------------------- new boards
    def new_board(self, board, source):
        """Put a board on screen and clear anything measured from the old one."""
        self.stop_replay()
        self.initial = board
        self.board = board
        self.source = source
        self.player_moves = []
        self.solution_nodes = None
        self.solution_moves = []
        self.solved = board == self.goal
        self.gave_up = False
        self.source_label.config(text=f"Board: {source}      Goal: 1-8 then the blank")
        self.clear_log()
        self.refresh_board()
        if self.solved:
            self.set_status("That is the goal board already.", OK)
        else:
            self.set_status(*self.default_status())

    def load_from_file(self, path=None):
        """Read the two boards from a file, the way Part 2 does."""
        if path is None:
            path = filedialog.askopenfilename(initialdir=str(HERE),
                                              filetypes=[("Text files", "*.txt")])
            if not path:
                return False
        try:
            initial, goal = read_boards(path)
        except ValueError as error:
            self.set_status(f"Could not read that file: {error}", BAD)
            return False
        self.goal = goal
        self.new_board(initial, Path(path).name)
        self.log_row("board", Path(path).name)
        return True

    def random_board(self):
        """A random solvable board: walk legal moves away from the goal, then load it."""
        import random
        state, previous = self.goal, None
        for _ in range(40):
            options = get_possible_moves(state)
            choices = [key for key in options if key != previous] or list(options)
            key = random.choice(choices)
            state, previous = options[key], UNDO[key]
        self.new_board(state, "a random board (40 moves from the goal)")
        self.log_row("board", "random, walked back from the goal")
        return True

    def reset_board(self):
        self.new_board(self.initial, self.source)
        self.set_status("Back at the start board.", INK)

    # ------------------------------------------------------------------ play
    def play(self, key):
        """Apply one legal move, if it is legal, and check for the goal."""
        if self.solved or self.replay_job is not None:
            return False
        options = get_possible_moves(self.board)
        if key not in options:
            self.set_status(f"There is no tile to the {MOVES[key][0].lower()} of the blank.", BAD)
            return False
        self.board = options[key]
        self.player_moves.append(key)
        self.refresh_board(highlight=key)
        if self.board == self.goal:
            self.solved = True
            self.set_status(f"Solved in {len(self.player_moves)} moves: "
                            f"{' '.join(self.player_moves)}", OK)
            self.log_row("you", f"{len(self.player_moves)} moves")
            self.compare_with_astar()
        else:
            self.set_status(f"Your move {len(self.player_moves)}: blank moved "
                            f"{MOVES[key][0].lower()}.", INK)
        return True

    def click_tile(self, index):
        """Clicking a tile next to the blank slides it into the blank."""
        blank = self.board.index(BLANK)
        key = CLICK_KEYS.get(blank - index)
        if key is None:
            self.set_status("Only a tile next to the empty space can move.", MUTED)
            return False
        return self.play(key)

    def on_board_click(self, event):
        index = self.cell_at(event.x, event.y)
        if index is not None:
            self.click_tile(index)

    def on_board_hover(self, event):
        index = self.cell_at(event.x, event.y)
        blank = self.board.index(BLANK)
        hover = index if index is not None and blank - index in CLICK_KEYS else None
        self.refresh_board(hover=hover)

    def cell_at(self, x, y):
        for index, (x1, y1, x2, y2) in enumerate(self.cell_boxes):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return index
        return None

    # ---------------------------------------------------------------- search
    def solve_now(self, start=None):
        """Run A* from `start` and keep its answer. Returns the node, or None."""
        start = self.board if start is None else start
        if not is_solvable(start, self.goal):
            self.set_status("This board cannot reach the goal, so there is nothing to search.",
                            BAD)
            return None
        node, expanded = astar(start, self.goal, successors, HEURISTICS[self.heuristic_name][0])
        self.solution_nodes = node
        self.solution_moves = [] if node is None else [step.action for step in path_of(node)[1:]]
        label = HEURISTICS[self.heuristic_name][1]
        if node is None:
            self.log_row("A*", f"no route found ({expanded} states expanded)")
            return None
        self.log_row("heuristic", label)
        self.log_row("A*", f"{node.g_cost} moves, {expanded} states expanded")
        self.log_row("sequence", ' '.join(self.solution_moves) or '(none)')
        return node

    def compare_with_astar(self):
        """After the player wins, put A*'s count next to theirs."""
        node = self.solve_now(self.initial)
        if node is None:
            return
        same = node.g_cost == len(self.player_moves)
        self.set_status(f"You: {len(self.player_moves)} moves. A*: {node.g_cost}. "
                        + ("The same answer." if same else "A* is shorter."), OK)

    def show_solution(self):
        """Play A*'s answer from the start board, one move at a time."""
        if self.replay_job is not None:            # already animating
            return False
        if self.solution_nodes is None:
            node = self.solve_now(self.initial)
            if node is None:
                return False
        self.stopped = False
        self.replay_index = 0
        self.board = self.initial
        self.solved = False
        self.refresh_board()
        self.log_row("replay", f"{len(self.solution_moves)} moves from the start board")
        self.stop_button.config(state="normal")
        self.replay_job = self.root.after(STEP_MS, self.step_replay)
        return True

    def step_replay(self):
        """One step of the animation, then schedule the next one."""
        if self.replay_index >= len(self.solution_moves):
            self.replay_job = None
            self.stop_button.config(state="disabled")
            self.board = self.goal
            self.refresh_board()
            self.set_status(f"A* solved it in {len(self.solution_moves)} moves: "
                            f"{' '.join(self.solution_moves) or '(none)'}", OK)
            return False
        key = self.solution_moves[self.replay_index]
        self.board = get_possible_moves(self.board)[key]
        self.replay_index += 1
        self.refresh_board(highlight=key)
        self.set_status(f"A* move {self.replay_index} of {len(self.solution_moves)}: "
                        f"blank moved {MOVES[key][0].lower()}.", MUTED)
        self.replay_job = self.root.after(STEP_MS, self.step_replay)
        return True

    def stop_replay(self):
        """Stop the animation where it is."""
        if self.replay_job is not None:
            self.root.after_cancel(self.replay_job)
            self.replay_job = None
            self.stop_button.config(state="disabled")
            self.refresh_board()
            self.log_row("replay", f"stopped at move {self.replay_index}")
        return True

    # ----------------------------------------------------------------- output
    def refresh_board(self, highlight=None, hover=None):
        """Draw the board. `highlight` is the key just played, `hover` a movable tile."""
        moved = self.previous_cell(highlight) if highlight else None
        for index, value in enumerate(self.board):
            if index == moved:
                fill, ink, edge, text = TILE_MOVED, TILE_INK_MOVED, TILE_MOVED, str(value)
            elif value == BLANK:
                fill, ink, edge, text = HOLE, MUTED, HOLE, ""
            elif index == hover:
                fill, ink, edge, text = TILE_HOVER, INK, TILE_MOVED, str(value)
            else:
                fill, ink, edge, text = TILE, INK, TILE_EDGE, str(value)
            self.board_canvas.itemconfig(self.tile_shapes[index], fill=fill, outline=edge)
            self.board_canvas.itemconfig(self.tile_labels[index], text=text, fill=ink)

    def previous_cell(self, key):
        """The cell the blank came from, for the highlight. `key` is the blank's move."""
        blank = self.board.index(BLANK)
        step = {'W': 3, 'A': 1, 'X': -3, 'D': -1}[key]
        previous = blank + step
        return previous if 0 <= previous < 9 else None

    def drawn_board(self):
        """What is on screen, for the checks."""
        return [self.board_canvas.itemcget(label, "text") for label in self.tile_labels]

    def set_status(self, text, colour=INK):
        self.status.config(text=text, fg=colour)
        self.status_accent.config(bg=colour)

    def log_row(self, label, text):
        """One log line, two columns so the numbers line up."""
        self.write_log(f"{label:<11}{text}")

    def write_log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")


def open_window(mode="play"):
    """Open the window and hand it the sample board if the file is there."""
    try:
        root = tk.Tk()
    except tk.TclError as error:
        sys.exit(f"No window available ({error}). Run this from a desktop session.")
    app = PuzzleGUI(root, mode=mode)
    default = HERE / DEFAULT_FILE
    if default.exists():
        app.load_from_file(str(default))
    root.mainloop()

# ==============================================================================
# PART 4 - the menu
# ==============================================================================

def ask(question, options):
    """Ask a question with a fixed set of answers and return the key chosen."""
    print(question)
    for key, text in options:
        print(f"  {key} - {text}")
    print("  Q - quit")
    for _ in range(3):
        try:
            choice = input("\nChoice: ").strip().upper()
        except EOFError:
            print("\nNo input left.")
            return None
        if choice == 'Q':
            return None
        if choice in dict(options):
            return choice
        print("Type " + ", ".join(key for key, _ in options) + " or Q.")
    print("No valid choice, stopping.")
    return None


def task2_demo():
    """Task 2: A* on the small weighted graph in this file."""
    print("\n=== A* on a small weighted graph ===")
    node, expanded = astar("S", "G", graph_successors, graph_heuristic, verbose=True)
    print()
    print_path(node)
    print(f"Nodes expanded: {expanded}")


def read_input_file():
    """Ask for the input file and read the two boards from it."""
    try:
        answer = input(f"Path to input file (press Enter for {DEFAULT_FILE}): ").strip()
    except EOFError:
        print("\nNo input left.")
        return None, None
    path = answer or str(HERE / DEFAULT_FILE)
    try:
        return read_boards(path)
    except ValueError as error:
        print(f"Input error: {error}")
        return None, None


def task3_cli(compare_heuristics=False):
    """Task 3 in the terminal: the two boards, then the search."""
    initial, goal = read_input_file()
    if initial is None:
        return
    print()
    print_boards(initial, goal, "the file")
    if compare_heuristics:
        compare(initial, goal)
    else:
        solve(initial, goal)


def main_menu():
    """The entry point: the window, or the terminal and a task."""
    print("DS 170 / CMSC 170 - Laboratory Exercise No. 4")
    print("A* algorithm and the 8-puzzle\n")

    mode = ask("How do you want to run the program?",
               [("1", "with a window (Task 3: play the puzzle, or let A* solve it)"),
                ("2", "in this terminal")])
    if mode is None:
        print("Goodbye.")
        return

    if mode == '1':
        # The window loads its own board from the file picker and has both tasks in it,
        # so there is nothing more to ask. The Task 2 demo stays in the terminal.
        open_window("solve")
        return

    task = ask("What do you want to do?",
               [("1", "run the Task 2 demo on the small graph"),
                ("2", "solve a puzzle from a file with A* (Task 3)"),
                ("3", "compare the two heuristics on a file (Task 3)")])
    if task is None:
        print("Goodbye.")
        return

    if task == '1':
        task2_demo()
    elif task == '2':
        task3_cli()
    else:
        task3_cli(compare_heuristics=True)


if __name__ == "__main__":
    main_menu()
