"""Inspectable project agents: Random, Minimax/Alpha-Beta and MCTS/UCT.

All agents use the same Position, legal moves and evaluation.
"""
from dataclasses import dataclass
from math import log, sqrt, tanh
from random import Random
from time import monotonic

from .engine import Position, SearchInfo, choose_move


@dataclass
class Report:
    name: str
    depth: int = 0
    nodes: int = 0
    milliseconds: int = 0
    score: float = 0
    iterations: int = 0
    rollouts: int = 0
    root: list | None = None


class Node:
    def __init__(self, position, rng, move=None, parent=None):
        self.position, self.move, self.parent = position, move, parent
        self.untried = position.legal()
        self.terminal = not self.untried
        rng.shuffle(self.untried)
        self.children = []
        self.visits = 0
        self.total = 0.0  # Every node stores reward from the ROOT player's view.


def mcts(position, *, iterations=1000, seconds=3, rollout_depth=10, seed=7, exploration=1.4):
    if iterations < 1 or rollout_depth < 0 or exploration < 0 or (seconds is not None and seconds <= 0):
        raise ValueError('Ngân sách tìm kiếm không hợp lệ.')
    started = monotonic()
    deadline = started + seconds if seconds is not None else float('inf')
    rng, perspective = Random(seed), position.turn
    root = Node(position, rng)
    if root.terminal:
        raise ValueError('Không còn nước hợp lệ.')
    nodes, completed, rollouts = 1, 0, 0

    def reward(state, legal):
        if not legal:
            return 1.0 if -state.turn == perspective else -1.0
        # A bounded positional estimate when a rollout stops before game end.
        # It is NOT a random result or an assertion of the actual winner.
        return tanh(state.score() * state.turn * perspective / 1200)

    def simulate(state, seen):
        for _ in range(rollout_depth):
            legal = state.legal()
            if not legal or monotonic() >= deadline:
                return reward(state, legal)
            state = state.apply(rng.choice(legal))
            key = (state.board, state.turn)
            if key in seen:
                return 0.0
            seen.add(key)
        return reward(state, state.legal())

    for _ in range(iterations):
        if completed and monotonic() >= deadline:
            break
        node, seen = root, {(root.position.board, root.position.turn)}
        repeated = False
        # Selection: the opponent maximizes its OWN result, not our result.
        while not node.untried and node.children:
            sign = 1 if node.position.turn == perspective else -1
            node = max(node.children, key=lambda child: sign * child.total / child.visits
                       + exploration * sqrt(log(node.visits) / child.visits))
            key = (node.position.board, node.position.turn)
            if key in seen:
                repeated = True
                break
            seen.add(key)
        # Expansion: exactly one previously untried legal move.
        if not repeated and node.untried:
            move = node.untried.pop()
            child = Node(node.position.apply(move), rng, move, node)
            node.children.append(child)
            node, nodes = child, nodes + 1
            key = (node.position.board, node.position.turn)
            repeated = key in seen
            seen.add(key)
        # Simulation: uniform legal rollouts, then the shared position score.
        if repeated:
            value = 0.0
        else:
            if not node.terminal:
                rollouts += 1
            value = simulate(node.position, seen)
        # Backpropagation: same root-relative reward all the way to the root.
        while node is not None:
            node.visits += 1
            node.total += value
            node = node.parent
        completed += 1
    best = max(root.children, key=lambda child: (child.visits, child.total / child.visits,
                                                -child.move[0], -child.move[1]))
    stats = [dict(move=list(child.move), visits=child.visits, mean=child.total / child.visits)
             for child in sorted(root.children, key=lambda child: child.move)]
    return best.move, Report('MCTS / UCT', nodes=nodes, iterations=completed, rollouts=rollouts,
                             milliseconds=round((monotonic() - started) * 1000),
                             score=best.total / best.visits, root=stats)


def choose(position: Position, agent='minimax', difficulty='medium', *, seed=7):
    if agent not in ('minimax', 'mcts', 'random'):
        raise ValueError('Thuật toán không hợp lệ.')
    started = monotonic()
    budget = {'easy': .25, 'medium': 1.0, 'hard': 3.0}[difficulty]
    if agent == 'mcts':
        return mcts(position, iterations={'easy': 100, 'medium': 500, 'hard': 2000}[difficulty],
                    seconds=budget, seed=seed)
    if agent == 'random':
        moves = position.legal()
        if not moves:
            raise ValueError('Không còn nước hợp lệ.')
        return Random(seed).choice(moves), Report('Ngẫu nhiên', milliseconds=round((monotonic() - started) * 1000))
    info = SearchInfo()
    move = choose_move(position, 'hard', seconds=budget,
                       max_depth={'easy': 2, 'medium': 5, 'hard': 8}[difficulty], info=info)
    return move, Report('Minimax / Alpha-Beta', depth=info.depth, nodes=info.nodes + info.qnodes,
                         milliseconds=round(info.elapsed * 1000), score=info.score)
