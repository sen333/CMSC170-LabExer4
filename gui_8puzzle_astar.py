"""
DS 170 / CMSC 170 - Laboratory Exercise No. 4
Task 3, the window: play the 8-puzzle, then watch A* solve it.

Group I
    Senoy, Kyle Howard            <student number>
    Jomuad, Precious Mae E.       2023-00554
    Royo, Dave Christian          <student number>

The window is the same program as Lab4_Task3.py, only drawn. The rules, the file
reader and the two heuristics all come from that file, so there is one copy of each,
and the search is the astar() that Lab4_Task2.py defines.

Run it from the folder that holds the input files:

    python3 gui_8puzzle_astar.py

A desktop session is needed. Over SSH it stops with "no display name and no $DISPLAY".

The board is a tuple of nine ints with 0 for the blank, so the window and the search
never have to convert anything. Clicking a tile next to the blank slides it; the keys
W, A, X and D move the blank, the same keys the lab sheet uses.

The buttons are in the order the player needs them: "Solve with A*" works from the
first move, so a stuck player can see the whole route instead of hunting for the next move.
"""

import sys
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog

from Lab4_Task2 import astar, path_of
from Lab4_Task3 import (BLANK, GOAL_A, HEURISTICS, MOVES, get_possible_moves,
                        is_solvable, inversions, read_boards, successors)

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
        """Read the two boards from a file, the way Lab4_Task3.py does."""
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


if __name__ == "__main__":
    open_window()
