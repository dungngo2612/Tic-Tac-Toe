"""Score five-cell windows for both sides, including open runs and gaps."""

from functools import lru_cache

from ..game.rules import geometry
from ..game.state import EMPTY, X, GameState

WIN_SCORE = 1_000_000
HEURISTIC_LIMIT = WIN_SCORE // 2


@lru_cache(maxsize=4096)
def _pattern(marks: tuple[int, ...]) -> tuple[int, int]:
    """Return signed positional points and the side one move away from winning."""
    side = EMPTY
    occupied = run = longest = 0
    for mark in marks:
        if mark == EMPTY:
            run = 0
            continue
        if side and mark != side:
            return 0, EMPTY
        side = mark
        occupied += 1
        run += 1
        longest = max(run, longest)
    if not occupied:
        return 0, EMPTY
    points = 8 ** occupied * (longest + 1)
    threat = side if occupied == len(marks) - 1 else EMPTY
    return side * points, threat


def evaluate(state: GameState, player: int) -> int:
    """Score from player's perspective. Only terminal positions reach WIN_SCORE."""
    if state.outcome is not None:
        return WIN_SCORE * state.outcome * player
    points = 0
    mover_can_win = False
    for window in geometry(state.rules).windows:
        value, threat = _pattern(tuple(state.board[cell] for cell in window))
        points += value
        mover_can_win |= threat == state.turn
    return positional_score(points, state.turn if mover_can_win else EMPTY, player)


def positional_score(points: int, winning_mover: int, player: int) -> int:
    """Bound positional points and add the bonus for a winning move on turn."""
    positional_limit = HEURISTIC_LIMIT // 4
    points = max(-positional_limit, min(points, positional_limit))
    points += winning_mover * (HEURISTIC_LIMIT - positional_limit)
    return points if player == X else -points
