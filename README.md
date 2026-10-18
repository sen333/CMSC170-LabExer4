# Lab 4 - A\* on the 8-puzzle (member 2's part)

Lab 4 asks for the A\* algorithm in Python and then for the same search applied to the
8-puzzle, with both boards read from a file. The core search was already on `main`; this
branch adds the puzzle, the file reader and the window, and joins them into the single
file that gets submitted.

    Lab4_Task2.py                    the core A* search (member 1, unchanged)
    Lab4_Task3.py                    the 8-puzzle: file reader, checks, moves, heuristics
    gui_8puzzle_astar.py             the window
    CMSC170_Lab4_AStar_8Puzzle.py    the three joined into one file, which is the submission
    sample_8_moves.txt               the 8-move board used in the runs
    handout_board.txt                the pair printed in the lab sheet (see below)
    already_solved.txt               initial board equal to the goal
    unsolvable_swap.txt              two tiles swapped, so the parity check refuses it
    invalid_*.txt, missing_goal.txt  broken files the reader is expected to refuse
    test_lab4.py                     the check battery, not part of the submission

## How to run it

    python3 CMSC170_Lab4_AStar_8Puzzle.py          # menu: window or terminal, then the task
    python3 Lab4_Task3.py                          # Task 3 straight from sample_8_moves.txt
    python3 Lab4_Task3.py --file handout_board.txt
    python3 Lab4_Task3.py --compare                # both heuristics, side by side
    python3 gui_8puzzle_astar.py                   # the window on its own

The window needs a desktop session. Over SSH it stops with "no display name and no
$DISPLAY environment variable".

## The input file

Three rows of three comma-separated numbers for the initial board, then three rows for the
goal board, with 0 for the blank:

    1,5,2
    7,4,3
    8,6,0

    1,2,3
    4,5,6
    7,8,0

Blank lines, `#` comments and label lines such as `Initial State` are skipped. Every cell
has to be a digit, and the nine cells have to be the tiles 0 to 8 exactly once.

## The handout's board cannot be solved

The initial board printed in the lab sheet, 1,2,3 / 8,0,4 / 7,6,5, has 7 inversions against
its goal's 0, so the two have different parity and no sequence of moves reaches one from the
other. The program checks that before searching and says so, and `handout_board.txt` keeps
that pair as a test case. `sample_8_moves.txt` is the solvable board used in the runs.

## Checks

    python3 test_lab4.py
