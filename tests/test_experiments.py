import csv
from pathlib import Path

import pytest

from tictactoe.ai.guarded_agent import GuardedAgent
from tictactoe.ai.mcts import MCTSAgent
from tictactoe.experiments.benchmark import run_benchmark
from tictactoe.experiments.plot import summarize
from tictactoe.experiments.verify import verify_policy
from tictactoe.game.rules import Rules
from tictactoe.game.state import O, X, State
from tictactoe.web import game_response

FIXTURES = Path(__file__).parent / "fixtures" / "tactical_positions.json"


@pytest.mark.parametrize("side", [X, O])
def test_verification_replays_a_real_counterexample_and_guard_prevents_losses(side):
    pure = MCTSAgent(1)
    result = verify_policy(pure, side, seed=7)
    assert result.losses > 0
    final = State.from_moves(Rules(3, 3), result.counterexample)
    assert final.outcome == -side
    guarded = verify_policy(GuardedAgent(pure), side, seed=7)
    assert guarded.losses == 0 and guarded.draws > 0 and guarded.counterexample is None


def test_benchmark_pairs_openings_sides_and_seeds_and_exports_moves(tmp_path):
    config = {
        "game": {"board_size": 3, "win_length": 3},
        "opponent": {"kind": "random"},
        "mcts": {"c": [1.4], "radius": 2},
        "smoke": {
            "iterations": [2, 4], "seeds": [7], "openings": [[4, 0]],
            "comparison_iterations": 2, "comparison_seconds": 0.001, "tactical_iterations": 2,
        },
    }
    paths = run_benchmark(config, "smoke", tmp_path, FIXTURES, notify=lambda _: None)
    with paths["games"].open(newline="") as stream:
        games = list(csv.DictReader(stream))
    with paths["moves"].open(newline="") as stream:
        moves = list(csv.DictReader(stream))
    assert len(games) == 12
    assert games[0]["mcts_side"] == "X" and games[1]["mcts_side"] == "O"
    assert games[0]["opening"] == games[1]["opening"] == "[4, 0]"
    assert games[0]["seed"] == games[1]["seed"] == "7"
    for game in games:
        played = [int(row["move"]) for row in moves if row["game_id"] == game["game_id"]]
        assert State.from_moves(Rules(3, 3), [4, 0, *played]).outcome is not None
    assert all(entry["games"] == 2 for entry in summarize(paths["games"]))


def test_web_validates_moves_and_uses_the_same_engine():
    board = game_response({"size": 3, "moves": [0, 3, 1, 4, 2]})["state"]
    assert board["outcome"] == X and board["line"] == (0, 1, 2)
    played = game_response({"size": 15, "moves": [112], "action": "ai", "agent": "minimax"})
    assert played["state"]["board"][played["search"]["move"]] == O
    for data in (
        {"moves": [1, 1]}, {"size": 5}, {"size": 3.0}, {"moves": [True]},
        {"action": "ai", "human": X}, {"action": "ai", "human": O, "iterations": 100.0},
        {"action": "ai", "human": O, "difficulty": "invalid"},
    ):
        with pytest.raises(ValueError):
            game_response(data)


@pytest.mark.parametrize(("size", "moves", "blocking_move"), [
    (3, [0, 4, 1], 2),
    (15, [0, 60, 1, 80, 2, 101, 3], 4),
])
def test_web_difficulty_presets_use_distinct_strategies(size, moves, blocking_move):
    opening = {"size": size, "action": "ai", "seed": 7, "moves": moves}

    easy = game_response({**opening, "difficulty": "easy"})["search"]
    assert easy["move"] != blocking_move
    assert easy["nodes"] == 0

    medium = game_response({**opening, "difficulty": "medium"})["search"]
    assert (medium["move"], medium["reason"]) == (blocking_move, "block")

    hard = game_response({**opening, "difficulty": "hard", "agent": "random", "depth": 1})["search"]
    assert hard["move"] == blocking_move
    if size == 15:
        assert hard["reason"] == "block"
    else:
        assert hard["nodes"] > 1
