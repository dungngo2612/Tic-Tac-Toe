from random import Random

import pytest

from tictactoe.ai.rollout import HeuristicRollout, RandomRollout
from tictactoe.ai.tactics import ThreatIndex, immediate_moves
from tictactoe.game.rules import Rules
from tictactoe.game.state import O, X, State


class RecordingRandom(Random):
    def __init__(self, seed):
        super().__init__(seed)
        self.choices = []

    def choice(self, cells):
        self.choices.append(tuple(cells))
        return super().choice(cells)


def test_heuristic_prioritizes_winning_blocking_and_strong_threats():
    rules = Rules(15, 5)
    for moves, expected in (
        ([107, 0, 108, 2, 110, 4, 111, 6], {109}),
        ([108, 109, 0, 110, 2, 111, 4, 112], {113}),
        ([109, 0, 110, 2, 111, 4], {108, 112}),
        ([0, 108, 2, 109, 4, 110, 6, 111, 8], {107, 112}),
    ):
        rng = RecordingRandom(17)
        result = HeuristicRollout().run(State.from_moves(rules, moves), rng)
        assert result in {X, O, 0}
        assert set(rng.choices[0]) == expected


@pytest.mark.parametrize("rules", [Rules(3, 3), Rules(15, 5)])
def test_incremental_threats_match_direct_win_detection(rules):
    state = State.empty(rules)
    threat = ThreatIndex(rules, list(state.board))
    rng = Random(42)
    while state.outcome is None:
        for side in (X, O):
            assert set(threat.wins[side]) == set(immediate_moves(state, side, state.legal_moves()))
        move = rng.choice(state.legal_moves())
        threat.place(move, state.turn)
        state = state.play(move)


def test_seeded_rollouts_replay_and_keep_terminal_value():
    initial = State.from_moves(Rules(3, 3), [0, 4, 1])
    terminal = State.from_moves(Rules(3, 3), [0, 3, 1, 4, 2])
    for rollout in (RandomRollout(), HeuristicRollout()):
        assert rollout.run(terminal, Random(1)) == X
        assert rollout.run(initial, Random(7)) == rollout.run(initial, Random(7))


def test_fork_priority_on_attack_and_defense_and_both_seeded_ties():
    rules = Rules(15, 5)
    # A contiguous three on row 8. Either end makes a four with two winning cells.
    for moves in ([109, 0, 110, 2, 111, 4], [0, 109, 2, 110, 4, 111]):
        state = State.from_moves(rules, moves)
        choices = ThreatIndex(rules, state.board).preferred_moves(state.turn)
        assert choices == [108, 112]
        selected = {Random(seed).choice(choices) for seed in range(16)}
        assert selected == {108, 112}


def test_heuristic_replays_every_move_for_both_sides_using_the_engine():
    class ReplayRandom(Random):
        def __init__(self, seed):
            super().__init__(seed)
            self.moves = []

        def choice(self, cells):
            move = super().choice(cells)
            self.moves.append(move)
            return move

    for seed in (7, 42):
        start = State.empty(Rules(3, 3))
        rng = ReplayRandom(seed)
        winner = HeuristicRollout().run(start, rng)
        replay = start
        for move in rng.moves:
            moves = replay.legal_moves()
            priority = (immediate_moves(replay, replay.turn, moves)
                        or immediate_moves(replay, -replay.turn, moves))
            assert move in (priority or moves)
            replay = replay.apply_move(move)
        assert replay.outcome == winner
        assert start.ply == 0


def test_shuffled_random_rollout_matches_engine_until_first_win():
    for rules in (Rules(3, 3), Rules(15, 5)):
        start = State.empty(rules)
        for seed in (7, 19, 42):
            order = list(start.legal_moves())
            Random(seed).shuffle(order)
            replay = start
            for move in order:
                replay = replay.apply_move(move)
                if replay.outcome is not None:
                    break
            assert RandomRollout().run(start, Random(seed)) == replay.outcome


def test_overlapping_windows_with_the_same_winning_square_are_not_a_fork():
    rules = Rules(15, 5)
    state = State.from_moves(rules, [108, 0, 109, 2, 112, 4, 113, 6])
    threats = ThreatIndex(rules, state.board)
    candidate = 110
    assert threats.pressure[X][candidate] >= 2
    after = state.apply_move(candidate)
    assert immediate_moves(after, X, after.legal_moves()) == (111,)
    # D8..I8 contains two candidate windows, but both need the same empty cell.
    assert not threats._creates_fork(candidate, X)
