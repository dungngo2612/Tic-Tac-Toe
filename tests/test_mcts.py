import sys
from math import inf, log, sqrt
from random import Random

import pytest

from tictactoe.ai.agent import MoveStat
from tictactoe.ai.guarded_agent import GuardedAgent
from tictactoe.ai.mcts import MCTSAgent, Node, backpropagate, select_child, select_root, uct
from tictactoe.ai.rollout import HeuristicRollout, RandomRollout
from tictactoe.ai.minimax import exact_value
from tictactoe.cli import coordinate
from tictactoe.game.match import turn_rng
from tictactoe.game.rules import CLASSIC_RULES, Rules
from tictactoe.game.state import O, X, State


def test_uct_and_root_policies():
    node = Node(State.empty(Rules(3, 3)))
    assert uct(node, 5, 1.4) == inf
    node.visits, node.wins = 10, 6
    assert uct(node, 30, 1.4) == pytest.approx(0.6 + 1.4 * sqrt(log(30) / 10))
    root = (MoveStat(1, 200, 0.65), MoveStat(2, 3, 1))
    assert select_root(root, "max_visits").move == 1
    assert select_root(root, "max_mean").move == 2


@pytest.mark.parametrize(("winner", "reward"), [(X, 1), (0, 0.5), (O, 0)])
def test_child_rewards_belong_to_the_mover(winner, reward):
    class FixedRollout:
        def run(self, state, rng):
            return winner

    result = MCTSAgent(9, rollout=FixedRollout()).choose(State.empty(Rules(3, 3)), seed=7)
    assert len(result.root) == 9
    assert {stat.mean for stat in result.root} == {reward}
    assert result.rollouts == sum(stat.visits for stat in result.root)


def test_different_final_policies_use_the_same_seeded_search_tree():
    state = State.from_moves(Rules(3, 3), [0, 4, 8])
    visits = MCTSAgent(100).choose(state, seed=7)
    mean = MCTSAgent(100, policy="max_mean").choose(state, seed=7)
    assert visits.root == mean.root
    assert visits.move == mean.max_visits
    assert mean.move == visits.max_mean
    assert visits.move != mean.move
    # Both moves can also be selected from the very first search result alone.
    assert select_root(visits.root).move == visits.max_visits
    assert select_root(visits.root, "max_mean").move == visits.max_mean


def test_guard_keeps_exact_value_even_with_one_iteration():
    state = State.from_moves(Rules(3, 3), [0, 4, 8])
    guard = GuardedAgent(MCTSAgent(1))
    for seed in range(24):
        result = guard.choose(state, seed)
        assert result.move in (1, 3, 5, 7)
        assert -exact_value(state.play(result.move)) == exact_value(state)


def test_tactical_ui_option_takes_an_immediate_win():
    state = State.from_moves(Rules(15, 5), [107, 0, 108, 2, 110, 4, 111, 6])
    result = MCTSAgent(1, tactical=True).choose(state, 7)
    assert (result.move, result.reason) == (109, "win")


def test_selection_at_the_opponent_node_chooses_the_opponents_win():
    # X plays B1. O can win with C2 or play A3, allowing X to win with C1.
    root = Node(State.from_moves(CLASSIC_RULES, [0, 3, 8, 4]))
    opponent = Node(root.state.apply_move(1), 1)
    blunder = Node(opponent.state.apply_move(6), 6)
    win_for_o = Node(opponent.state.apply_move(5), 5)
    win_for_x = Node(blunder.state.apply_move(2), 2)
    root.children = [opponent]
    opponent.children = [blunder, win_for_o]
    blunder.children = [win_for_x]
    assert root.state.turn == X and opponent.state.turn == O
    assert (win_for_o.state.outcome, win_for_x.state.outcome) == (O, X)

    backpropagate([root, opponent, win_for_o], O)
    assert (opponent.wins, win_for_o.wins) == (0, 1)
    assert select_child(opponent, exploration=1.4) is blunder  # Unvisited.
    backpropagate([root, opponent, blunder, win_for_x], X)
    assert (blunder.wins, win_for_x.wins) == (0, 1)
    assert (root.visits, opponent.visits, blunder.visits, win_for_o.visits) == (2, 2, 1, 1)
    assert select_child(opponent, exploration=1.4) is win_for_o


def test_terminal_leaves_count_iterations_without_calling_rollout():
    class CountRollouts:
        def __init__(self):
            self.calls = 0

        def run(self, state, rng):
            assert state.outcome is None
            self.calls += 1
            return RandomRollout().run(state, rng)

    rollout = CountRollouts()
    almost_full = State.from_moves(CLASSIC_RULES, [0, 1, 2, 4, 3, 5, 7])
    result = MCTSAgent(32, rollout=rollout).choose_move(almost_full, Random(7))
    assert result.iterations == 32 == sum(item.visits for item in result.root)
    assert result.rollouts == rollout.calls == 2
    assert result.nodes <= result.iterations + 1
    for item in result.root:
        assert 0 <= item.wins <= item.visits and (2 * item.wins).is_integer()
        assert item.mean == item.wins / item.visits
    one_move_left = almost_full.apply_move(6)
    result = MCTSAgent(8, rollout=rollout).choose_move(one_move_left, Random(7))
    assert result.iterations == 8 and result.rollouts == 0 and rollout.calls == 2
    assert result.nodes == 2
    only, = result.root
    assert (only.visits, only.wins, only.mean) == (8, 4, 0.5)


def test_final_ties_and_unvisited_moves():
    stats = (
        MoveStat(6, 4, wins=1.0), MoveStat(1, 4, wins=2.0),
        MoveStat(0, 4, wins=2.0), MoveStat(3, 2, wins=1.0),
    )
    for policy in ("max_visits", "max_mean"):
        assert select_root(stats, policy).move == 0
        with pytest.raises(ValueError):
            select_root((MoveStat(2, 0, wins=0.0),), policy)
    assert select_root((MoveStat(0, 0, wins=0), MoveStat(4, 1, wins=0)), "max_mean").move == 4
    result = MCTSAgent(2).choose_move(State.empty(CLASSIC_RULES), Random(17))
    assert len(result.root) == len({item.move for item in result.root}) == 2
    assert all(item.visits == 1 for item in result.root)


@pytest.mark.parametrize("rollout", [RandomRollout(), HeuristicRollout()])
def test_seed_reproduces_completed_search_for_each_rollout(rollout):
    state = State.from_moves(CLASSIC_RULES, [4, 0])
    mcts = MCTSAgent(64, exploration=0.5, rollout=rollout)
    a, b = (mcts.choose_move(state, Random(42)) for _ in range(2))
    assert a.root == b.root and a.move == b.move
    assert a.iterations == b.iterations == 64
    assert (a.max_visits, a.max_mean, a.nodes, a.rollouts) == (
        b.max_visits, b.max_mean, b.nodes, b.rollouts)
    assert a.elapsed >= 0


@pytest.mark.parametrize("budget", [0, -1, 1.5, True])
def test_iteration_budget_is_a_positive_integer(budget):
    with pytest.raises(ValueError):
        MCTSAgent(iterations=budget)


def test_terminal_reads_mcts_settings_and_cli_flags_override_toml(tmp_path, monkeypatch, capsys):
    from tictactoe.__main__ import main

    config = tmp_path / "game.toml"
    config.write_text(
        '[game]\nboard_size=3\nwin_length=3\nseed=19\n'
        '[mcts]\niterations=11\nc=0.5\nrollout="heuristic"\npolicy="max_mean"\nradius=0\n'
    )
    base = ["tictactoe", "play", "--config", str(config), "--agent", "mcts", "--human", "O"]
    monkeypatch.setattr("builtins.input", lambda _: "q")
    for extra, count, c, rollout, policy, seed in [
        ([], 11, 0.5, HeuristicRollout(), "max_mean", 19),
        (["--iterations", "23", "--c", "2", "--rollout", "random", "--policy", "max_visits", "--seed", "42"],
         23, 2.0, RandomRollout(), "max_visits", 42),
    ]:
        monkeypatch.setattr(sys, "argv", base + extra)
        main()
        output = capsys.readouterr().out
        state = State.empty(CLASSIC_RULES)
        expected = MCTSAgent(count, c, rollout, policy).choose_move(state, turn_rng(seed, state))
        assert f"AI X chọn {coordinate(expected.move, 3)} " in output
        assert f"{count} iteration, {expected.rollouts} rollout" in output


@pytest.mark.parametrize("moves", [[0, 3, 1, 4], [0, 4, 1]])
def test_pure_mcts_wins_as_x_or_blocks_as_o_in_small_positions(moves):
    state = State.from_moves(CLASSIC_RULES, moves)
    result = MCTSAgent(100).choose_move(state, Random(7))
    assert result.move == 2 and result.iterations == 100
    assert result.reason is None and result.root
