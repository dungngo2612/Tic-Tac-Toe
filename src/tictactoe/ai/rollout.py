"""Complete a simulation by sampling legal moves until the game ends."""

from dataclasses import dataclass
from random import Random
from typing import Protocol

from ..game.rules import geometry
from ..game.state import EMPTY, GameState
from .tactics import ThreatIndex


class Rollout(Protocol):
    """Return the terminal winner (X/O) or EMPTY for a draw."""

    def run(self, state: GameState, rng: Random) -> int: ...


def _has_won(board: list[int], rays: tuple[tuple[int, ...], ...], player: int, target: int) -> bool:
    for direction in range(0, 8, 2):
        count = 1
        for cell in rays[direction]:
            if board[cell] != player:
                break
            count += 1
        for cell in rays[direction + 1]:
            if board[cell] != player:
                break
            count += 1
        if count >= target:
            return True
    return False


@dataclass(frozen=True, slots=True)
class RandomRollout:
    def run(self, state: GameState, rng: Random) -> int:
        if state.outcome is not None:
            return state.outcome
        board = list(state.board)
        moves = list(state.legal_moves())
        rng.shuffle(moves)
        player = state.turn
        rays = geometry(state.rules).rays
        target = state.rules.connect
        for move in moves:
            board[move] = player
            if _has_won(board, rays[move], player, target):
                return player
            player = -player
        return EMPTY


@dataclass(frozen=True, slots=True)
class HeuristicRollout:
    def run(self, state: GameState, rng: Random) -> int:
        if state.outcome is not None:
            return state.outcome
        threats = ThreatIndex(state.rules, state.board)
        moves = list(state.legal_moves())
        positions = {move: index for index, move in enumerate(moves)}
        player = state.turn
        while moves:
            move = rng.choice(threats.preferred_moves(player) or moves)
            if move in threats.wins[player]:
                return player
            index = positions.pop(move)
            last = moves.pop()
            if index < len(moves):
                moves[index] = last
                positions[last] = index
            threats.place(move, player)
            player = -player
        return EMPTY
