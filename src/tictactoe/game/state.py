"""Immutable game state. Moves are zero-based row-major cell indexes."""

from collections.abc import Sequence
from dataclasses import dataclass

from .rules import Rules, geometry

X, O, EMPTY = 1, -1, 0
SYMBOLS = {X: "X", O: "O", EMPTY: "·"}


def winning_line(
    board: Sequence[int], move: int, player: int, rules: Rules
) -> tuple[int, ...]:
    rays = geometry(rules).rays[move]
    for direction in range(0, len(rays), 2):
        forward, backward = [], []
        for cell in rays[direction]:
            if board[cell] != player:
                break
            forward.append(cell)
        for cell in rays[direction + 1]:
            if board[cell] != player:
                break
            backward.append(cell)
        if 1 + len(forward) + len(backward) >= rules.connect:
            return (*reversed(backward), move, *forward)
    return ()


@dataclass(frozen=True, slots=True)
class GameState:
    """outcome is None during play, 0 on a draw, or the winning mark X/O."""

    rules: Rules
    board: tuple[int, ...]
    turn: int
    remaining: int
    outcome: int | None = None
    last_move: int | None = None
    line: tuple[int, ...] = ()

    @classmethod
    def empty(cls, rules: Rules = Rules()) -> "GameState":
        return cls(rules, (EMPTY,) * rules.cells, turn=X, remaining=rules.cells)

    @classmethod
    def from_moves(cls, rules: Rules, moves: Sequence[int]) -> "GameState":
        state = cls.empty(rules)
        for move in moves:
            state = state.apply_move(move)
        return state

    @property
    def ply(self) -> int:
        return self.rules.cells - self.remaining

    def legal_moves(self) -> tuple[int, ...]:
        if self.outcome is not None:
            return ()
        return tuple(move for move, mark in enumerate(self.board) if mark == EMPTY)

    def apply_move(self, move: int) -> "GameState":
        if self.outcome is not None:
            raise ValueError("Ván đấu đã kết thúc.")
        if type(move) is not int or not 0 <= move < self.rules.cells:
            raise ValueError("Nước đi nằm ngoài bàn cờ.")
        if self.board[move] != EMPTY:
            raise ValueError("Ô này đã có quân.")

        player = self.turn
        board = (*self.board[:move], player, *self.board[move + 1:])
        line = winning_line(board, move, player, self.rules)
        remaining = self.remaining - 1
        outcome = player if line else (EMPTY if remaining == 0 else None)
        return GameState(self.rules, board, -player, remaining, outcome, move, line)

    # Compatibility with the original state API.
    play = apply_move


State = GameState
