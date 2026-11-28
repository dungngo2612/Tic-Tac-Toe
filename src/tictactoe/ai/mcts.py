"""Monte Carlo tree search. Each child's reward belongs to its previous mover."""

from dataclasses import dataclass, field
from math import isfinite, log, sqrt
from random import Random
from time import perf_counter

from ..game.state import EMPTY, GameState
from .agent import MoveStat, SearchResult, SeededAgent
from .rollout import RandomRollout, Rollout
from .tactics import immediate_moves, nearby_moves


@dataclass(slots=True)
class Node:
    state: GameState
    move: int | None = None
    pending: list[int] = field(default_factory=list)
    children: list["Node"] = field(default_factory=list)
    visits: int = 0
    wins: float = 0.0

    @classmethod
    def create(cls, state: GameState, move: int | None, radius: int, rng: Random) -> "Node":
        pending = list(nearby_moves(state, radius))
        rng.shuffle(pending)
        return cls(state, move, pending)

    @property
    def mean(self) -> float:
        return self.wins / self.visits if self.visits else 0.0


def uct(child: Node, parent_visits: int, exploration: float) -> float:
    if child.visits == 0:
        return float("inf")
    return child.mean + exploration * sqrt(log(parent_visits) / child.visits)


def select_child(parent: Node, exploration: float) -> Node:
    # All children store reward for parent.state.turn, including at opponent nodes.
    # max keeps the earliest expanded child when UCT scores tie.
    return max(parent.children, key=lambda child: uct(child, parent.visits, exploration))


def backpropagate(path: list[Node], outcome: int) -> None:
    for node in path:
        previous_player = -node.state.turn
        node.visits += 1
        node.wins += 0.5 if outcome == EMPTY else float(outcome == previous_player)


def select_root(stats: tuple[MoveStat, ...], policy: str = "max_visits") -> MoveStat:
    """Rank visited root moves only. The final tie goes to the lower cell index."""
    visited = [item for item in stats if item.visits > 0]
    if not visited:
        raise ValueError("Không có nước gốc đã thăm để xếp hạng.")
    if policy == "max_visits":
        return max(visited, key=lambda item: (item.visits, item.mean, -item.move))
    if policy == "max_mean":
        return max(visited, key=lambda item: (item.mean, item.visits, -item.move))
    raise ValueError(f"Quy tắc chọn nước không hợp lệ: {policy}")


@dataclass(frozen=True, slots=True)
class MCTSAgent(SeededAgent):
    iterations: int = 100
    exploration: float = 1.4
    rollout: Rollout = field(default_factory=RandomRollout)
    policy: str = "max_visits"
    radius: int = 0
    seconds: float | None = None
    tactical: bool = False

    def __post_init__(self) -> None:
        if type(self.iterations) is not int or self.iterations < 1:
            raise ValueError("Ngân sách iteration phải là số nguyên dương.")
        if type(self.exploration) not in (int, float) or not isfinite(self.exploration) or self.exploration < 0:
            raise ValueError("Hệ số c phải hữu hạn và không âm.")
        if type(self.radius) is not int or self.radius < 0 or self.policy not in {"max_visits", "max_mean"}:
            raise ValueError("Bán kính hoặc quy tắc chọn nước không hợp lệ.")
        if self.seconds is not None and (not isfinite(self.seconds) or self.seconds <= 0):
            raise ValueError("Ngân sách thời gian phải hữu hạn và lớn hơn 0.")

    def choose_move(self, state: GameState, rng: Random) -> SearchResult:
        if state.outcome is not None:
            raise ValueError("Ván đấu đã kết thúc.")
        started = perf_counter()
        if self.tactical:
            candidates = nearby_moves(state, self.radius)
            wins = immediate_moves(state, state.turn, candidates)
            forced = wins or immediate_moves(state, -state.turn, candidates)
            if forced:
                return SearchResult(
                    rng.choice(forced), perf_counter() - started, nodes=1,
                    reason="win" if wins else "block",
                )

        root = Node.create(state, None, self.radius, rng)
        nodes, rollouts = 1, 0
        while True:
            node = root
            path = [root]
            while node.children and not node.pending:
                node = select_child(node, self.exploration)
                path.append(node)

            if node.pending:
                move = node.pending.pop()
                child = Node.create(node.state.apply_move(move), move, self.radius, rng)
                node.children.append(child)
                node = child
                path.append(node)
                nodes += 1

            outcome = node.state.outcome
            if outcome is None:
                outcome = self.rollout.run(node.state, rng)
                rollouts += 1
            backpropagate(path, outcome)

            if self.seconds is None:
                if root.visits >= self.iterations:
                    break
            elif perf_counter() - started >= self.seconds:
                break

        stats = tuple(
            MoveStat(child.move, child.visits, wins=child.wins)
            for child in root.children if child.move is not None and child.visits
        )
        by_visits = select_root(stats, "max_visits").move
        by_mean = select_root(stats, "max_mean").move
        return SearchResult(
            move=by_visits if self.policy == "max_visits" else by_mean,
            elapsed=perf_counter() - started, nodes=nodes,
            iterations=root.visits, rollouts=rollouts,
            max_visits=by_visits, max_mean=by_mean, root=stats,
        )
