"""Candidate ordering and incremental rollout threats."""

from collections.abc import Iterable, Sequence

from ..game.rules import Rules, geometry, neighborhoods
from ..game.state import EMPTY, GameState, winning_line


def nearby_moves(state: GameState, radius: int) -> tuple[int, ...]:
    if not radius or state.rules.size <= 3:
        return state.legal_moves()
    if state.outcome is not None:
        return ()
    if not state.ply:
        middle = state.rules.size // 2
        return (middle * state.rules.size + middle,)
    near = neighborhoods(state.rules.size, radius)
    candidates = {
        cell
        for move, mark in enumerate(state.board)
        if mark
        for cell in near[move]
        if state.board[cell] == EMPTY
    }
    return tuple(sorted(candidates)) or state.legal_moves()


def immediate_moves(
    state: GameState, player: int, moves: Iterable[int]
) -> tuple[int, ...]:
    return tuple(
        move for move in moves if winning_line(state.board, move, player, state.rules)
    )


def ordered_moves(
    state: GameState, radius: int = 0, limit: int = 0, *, prioritize_forks: bool = False,
) -> tuple[int, ...]:
    """Rank wins, blocks, optional forks, positional score, and distance to center."""
    lines = geometry(state.rules)
    player = state.turn
    size = state.rules.size
    candidates = nearby_moves(state, radius)
    wins = set(immediate_moves(state, player, candidates))
    blocks = set(immediate_moves(state, -player, candidates))
    if prioritize_forks and (wins or blocks):
        # Winning now takes precedence; any non-blocking reply otherwise loses at once.
        return tuple(sorted(wins or blocks))

    def priority(move: int) -> tuple[int, int, int, int]:
        score = 0
        attack_targets, defense_targets = set(), set()
        for index in lines.through[move]:
            window = lines.windows[index]
            marks = [state.board[cell] for cell in window]
            own = marks.count(player)
            opposing = marks.count(-player)
            if not opposing:
                score += 5 ** own
                if prioritize_forks and own == state.rules.connect - 2:
                    attack_targets.update(cell for cell in window if cell != move and not state.board[cell])
            if not own:
                score += 4 ** opposing
                if prioritize_forks and opposing == state.rules.connect - 2:
                    defense_targets.update(cell for cell in window if cell != move and not state.board[cell])
        row, col = divmod(move, size)
        distance = abs(2 * row - size + 1) + abs(2 * col - size + 1)
        attacking = move in wins or len(attack_targets) >= 2
        defending = move in blocks or len(defense_targets) >= 2
        tier = 2 if attacking else int(defending)
        return -tier, -score, distance, move

    ordered = tuple(sorted(candidates, key=priority))
    if limit and size > 3:
        return ordered[: max(limit, len(wins | blocks))]
    return ordered


class ThreatIndex:
    """Track each player's winning cells and ways to create winning threats."""

    def __init__(self, rules: Rules, board: Sequence[int]):
        self.rules = rules
        self.board = [EMPTY] * rules.cells
        self.lines = geometry(rules)
        self.counts = {side: [0] * len(self.lines.windows) for side in (1, -1)}
        self.wins: dict[int, dict[int, int]] = {1: {}, -1: {}}
        self.pressure: dict[int, dict[int, int]] = {1: {}, -1: {}}
        if rules.connect == 2:  # Only then do empty windows already contribute pressure.
            for index in range(len(self.lines.windows)):
                self._update(index, 1)
        for move, mark in enumerate(board):
            if mark:
                self.place(move, mark)

    def _update(self, index: int, delta: int) -> None:
        target = self.rules.connect
        for player in (1, -1):
            if self.counts[-player][index]:
                continue
            count = self.counts[player][index]
            if count == target - 1:
                scores = self.wins[player]
            elif count == target - 2:
                scores = self.pressure[player]
            else:
                continue
            for cell in self.lines.windows[index]:
                if self.board[cell] == EMPTY:
                    value = scores.get(cell, 0) + delta
                    if value:
                        scores[cell] = value
                    else:
                        del scores[cell]

    def threat_targets(self, move: int, player: int) -> set[int]:
        """Winning squares created by a move, including both ends and internal gaps."""
        if move not in self.pressure[player]:
            return set()
        targets = set()
        for index in self.lines.through[move]:
            if self.counts[-player][index] or self.counts[player][index] != self.rules.connect - 2:
                continue
            targets.update(cell for cell in self.lines.windows[index] if cell != move and self.board[cell] == EMPTY)
        return targets

    def _creates_fork(self, move: int, player: int) -> bool:
        return self.pressure[player].get(move, 0) >= 2 and len(self.threat_targets(move, player)) >= 2

    def preferred_moves(self, player: int) -> list[int]:
        """Return one priority tier. An empty list leaves every legal move tied."""
        immediate = self.wins[player] or self.wins[-player]
        if immediate:
            return sorted(immediate)
        attack, defense = self.pressure[player], self.pressure[-player]
        candidates = sorted(attack.keys() | defense.keys())
        forks = [move for move in candidates
                 if self._creates_fork(move, player) or self._creates_fork(move, -player)]
        if forks:
            return forks
        if not candidates:
            return []
        pressure = {move: attack.get(move, 0) + defense.get(move, 0) for move in candidates}
        best = max(pressure.values())
        return [move for move in candidates if pressure[move] == best]

    def place(self, move: int, player: int) -> None:
        self._change(move, player, 1)

    def remove(self, move: int) -> None:
        self._change(move, self.board[move], -1)

    def _change(self, move: int, player: int, delta: int) -> None:
        windows = self.lines.through[move]
        for index in windows:
            self._update(index, -1)
            self.counts[player][index] += delta
        self.board[move] = player if delta == 1 else EMPTY
        for index in windows:
            self._update(index, 1)
