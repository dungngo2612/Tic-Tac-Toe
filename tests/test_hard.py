import json
from pathlib import Path
from random import Random

import pytest

from tictactoe.ai import forcing
from tictactoe.ai.evaluation import WIN_SCORE, evaluate
from tictactoe.ai.tactics import ThreatIndex, immediate_moves
from tictactoe.game import GameState, Rules
from tictactoe.web import game_response, hard_agent

POSITIONS = json.loads((Path(__file__).parent / "fixtures" / "hard_positions.json").read_text())


@pytest.mark.parametrize("case", POSITIONS, ids=lambda case: case["id"])
def test_hard_15x15_tactics(case):
    state = GameState.from_moves(Rules(), case["moves"])
    agent = hard_agent()
    result = agent.choose_move(state, Random(7))
    assert result.move in case["expected"]
    assert result.reason == case.get("reason")
    assert (result.reason == "forced_loss") == case["forced_loss"]
    if case["forced_loss"]:
        for move in state.legal_moves():
            child = state.apply_move(move)
            assert immediate_moves(child, child.turn, child.legal_moves())
    if "proof_line" in case:
        assert result.score == WIN_SCORE - state.ply - len(case["proof_line"])
        assert result.completed_depth == 1
        attacker = state.turn
        for move in case["proof_line"]:
            if state.turn != attacker:
                assert not immediate_moves(state, state.turn, state.legal_moves())
                blocks = immediate_moves(state, attacker, state.legal_moves())
                assert move in blocks
                # Every other reply leaves some winning square open.
                for reply in state.legal_moves():
                    if reply != move or len(blocks) > 1:
                        child = state.apply_move(reply)
                        assert immediate_moves(child, attacker, child.legal_moves())
            state = state.apply_move(move)
        assert state.outcome == attacker


def test_deadline_retains_completed_depth_or_falls_back(monkeypatch):
    state = GameState.empty()
    time = 0
    evaluations = 0
    original = forcing._SearchThreats.evaluate

    def evaluate_until_depth_two(threats, player):
        nonlocal time, evaluations
        evaluations += 1
        if evaluations == 2:
            time = 2
        return original(threats, player)

    monkeypatch.setattr(forcing, "perf_counter", lambda: time)
    monkeypatch.setattr(forcing._SearchThreats, "evaluate", evaluate_until_depth_two)
    result = hard_agent().choose_move(state, Random(7))
    assert result.move == 112 and result.completed_depth == 1 and result.timed_out

    clock = iter([0, 2, 2])
    monkeypatch.setattr(forcing, "perf_counter", lambda: next(clock))
    result = hard_agent().choose_move(state, Random(7))
    assert result.move in state.legal_moves() and result.completed_depth == 0 and result.timed_out


def test_search_index_restores_threats_and_evaluation_on_undo():
    state = GameState.empty()
    threats = forcing._SearchThreats(state)
    moves = [112, 113, 128, 96, 142, 97, 158, 144, 82, 67]
    for move in moves:
        threats.place(move, state.turn)
        state = state.apply_move(move)
        assert threats.evaluate(state.turn) == evaluate(state, state.turn)
    for ply in range(len(moves) - 1, -1, -1):
        threats.remove(moves[ply])
        state = GameState.from_moves(Rules(), moves[:ply])
        clean = ThreatIndex(state.rules, state.board)
        assert (threats.wins, threats.pressure) == (clean.wins, clean.pressure)
        assert threats.evaluate(state.turn) == evaluate(state, state.turn)


def test_web_hard_uses_configured_search(tmp_path):
    config = tmp_path / "game.toml"
    config.write_text("[hard]\ndepth = 1\nseconds = 1.0\n", encoding="utf-8")
    result = game_response(
        {"size": 15, "difficulty": "hard", "action": "ai", "human": -1},
        hard=hard_agent(config),
    )["search"]
    assert result["completed_depth"] == 1
    assert not result["timed_out"]
