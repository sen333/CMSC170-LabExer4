"""
DS 170 / CMSC 170 - Laboratory Exercise No. 4
Task 2: A* Algorithm in Python (core, reusable)
"""

import heapq
import itertools


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


def _graph_successors(state):
    return state_space[state]


def _graph_heuristic(state, goal):
    return h_table[state]


if __name__ == "__main__":
    initial_state, goal_state = "S", "G"
    print("=== A* demo on a small weighted graph ===")
    node, expanded = astar(initial_state, goal_state, _graph_successors,
                           _graph_heuristic, verbose=True)
    print()
    print_path(node)
    print(f"Nodes expanded: {expanded}")
    # Optimal route is S -> A -> B -> C -> G with cost 8.
    assert node is not None and node.g_cost == 8

    # Reusability check: the same astar() solves the 8-puzzle when the project's
    # Task 2 move generator is next to this file.
    try:
        from Task2_Lab3 import get_possible_moves
    except ImportError:
        pass
    else:
        def puzzle_successors(s):
            return [(k, n, 1) for k, n in get_possible_moves(s).items()]

        def manhattan(s, g):
            pos = {t: i for i, t in enumerate(g)}
            return sum(abs(i // 3 - pos[t] // 3) + abs(i % 3 - pos[t] % 3)
                       for i, t in enumerate(s) if t != 0)

        start = (1, 5, 2, 7, 4, 3, 8, 6, 0)   # sample_8_moves.txt
        goal = (1, 2, 3, 4, 5, 6, 7, 8, 0)
        n, e = astar(start, goal, puzzle_successors, manhattan)
        print(f"\n8-puzzle check (Manhattan): moves={n.g_cost}, nodes expanded={e}")
