"""Paired benchmarks, tactical root comparison, and Alpha-Beta measurements."""

import csv
import json
from collections.abc import Callable
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from random import Random

from ..ai.agent import Agent
from ..ai.mcts import MCTSAgent
from ..ai.minimax import MinimaxAgent
from ..ai.random_agent import RandomAgent
from ..ai.rollout import HeuristicRollout, RandomRollout
from ..config import game_rules
from ..game.match import play_match
from ..game.rules import Rules
from ..game.state import O, X, GameState

ROLLOUTS = {"random": RandomRollout, "heuristic": HeuristicRollout}


@dataclass(frozen=True, slots=True)
class Trial:
    suite: str
    exploration: float
    iterations: int
    rollout: str = "random"
    seconds: float | None = None


def trials(config: dict, profile: str) -> list[Trial]:
    spec = config[profile]
    matrix = [
        Trial("matrix", c, count)
        for c, count in product(config["mcts"]["c"], spec["iterations"])
    ]
    for rollout in ROLLOUTS:
        matrix.append(Trial("rollout_iterations", 1.4, spec["comparison_iterations"], rollout))
        matrix.append(Trial("rollout_time", 1.4, 1, rollout, spec["comparison_seconds"]))
    return matrix


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def _paired_games(
    config: dict, profile: str, opponent: Agent, opponent_name: str,
    notify: Callable[[str], None],
) -> tuple[list[dict], list[dict]]:
    rules = game_rules(config)
    spec = config[profile]
    games, moves = [], []
    for trial in trials(config, profile):
        mcts = MCTSAgent(
            trial.iterations, trial.exploration, ROLLOUTS[trial.rollout](),
            radius=config["mcts"]["radius"], seconds=trial.seconds,
        )
        games_before = len(games)
        for opening_id, opening in enumerate(spec["openings"]):
            for seed in spec["seeds"]:
                for side, symbol in ((X, "X"), (O, "O")):
                    game_id = len(games) + 1
                    x, o = (mcts, opponent) if side == X else (opponent, mcts)
                    initial = GameState.from_moves(rules, opening)
                    final, played = play_match(rules, x, o, opening=tuple(opening), seed=seed)
                    own = []
                    opponent_moves = []
                    turn = initial.turn
                    for ply, decision in enumerate(played, start=initial.ply + 1):
                        (own if turn == side else opponent_moves).append(decision)
                        selected = next((item for item in decision.root if item.move == decision.move), None)
                        moves.append({
                            "game_id": game_id, "ply": ply, "side": "X" if turn == X else "O",
                            "agent": "mcts" if turn == side else opponent_name,
                            "move": decision.move, "elapsed_seconds": decision.elapsed,
                            "nodes": decision.nodes, "cutoffs": decision.cutoffs,
                            "completed_iterations": decision.iterations, "rollouts": decision.rollouts, "max_visits": decision.max_visits,
                            "max_mean": decision.max_mean, "selected_visits": selected.visits if selected else None,
                            "selected_w": selected.wins if selected else None,
                            "selected_mean": selected.mean if selected else None,
                        })
                        turn = -turn
                    games.append({
                        "game_id": game_id, "profile": profile, "suite": trial.suite,
                        "c": trial.exploration, "iterations": trial.iterations if trial.seconds is None else None,
                        "budget_seconds": trial.seconds, "rollout": trial.rollout, "root_policy": mcts.policy,
                        "mcts_radius": mcts.radius, "opponent": opponent_name, "mcts_side": symbol,
                        "opponent_depth": getattr(opponent, "depth", None),
                        "opponent_radius": getattr(opponent, "radius", None),
                        "opponent_candidate_limit": getattr(opponent, "candidate_limit", None),
                        "size": rules.size, "connect": rules.connect,
                        "opening_id": opening_id, "opening": json.dumps(opening), "seed": seed,
                        "result": "win" if final.outcome == side else ("draw" if final.outcome == 0 else "loss"),
                        "plies": final.ply, "mcts_moves": len(own),
                        "mcts_seconds": sum(decision.elapsed for decision in own),
                        "opponent_moves": len(opponent_moves),
                        "opponent_seconds": sum(decision.elapsed for decision in opponent_moves),
                        "mcts_iterations": sum(decision.iterations for decision in own),
                        "mcts_rollouts": sum(decision.rollouts for decision in own),
                    })
        budget = f"{trial.seconds}s" if trial.seconds else f"{trial.iterations} iter"
        notify(f"{trial.suite} · c={trial.exploration:g} · {budget} · {trial.rollout} · {len(games)-games_before} ván")
    return games, moves


def _compare_pruning(item: dict, state: GameState, *, depth: int, radius: int,
                     limit: int, seed: int) -> list[dict]:
    rows = []
    for enabled in (False, True):
        agent = MinimaxAgent(depth, enabled, radius, limit)
        decision = agent.choose_move(state, Random(seed))
        rows.append({
            "position": item["id"], "opening": json.dumps(item["moves"]), "size": state.rules.size,
            "connect": state.rules.connect, "turn": state.turn, "depth": depth, "radius": radius,
            "candidate_limit": limit, "seed": seed, "alpha_beta": enabled, "move": decision.move,
            "score": decision.score, "correct": decision.move in item["expected"],
            "nodes": decision.nodes, "cutoffs": decision.cutoffs, "elapsed_seconds": decision.elapsed,
        })
    return rows


def export_pruning(fixtures: Path, output: Path, *, depth: int, radius: int,
                   limit: int, seed: int) -> Path:
    """Replay each 15×15 fixture twice, changing only the pruning switch."""
    rows = []
    for item in json.loads(fixtures.read_text(encoding="utf-8")):
        if (item["size"], item["connect"]) == (15, 5):
            state = GameState.from_moves(Rules(15, 5), item["moves"])
            rows.extend(_compare_pruning(item, state, depth=depth, radius=radius, limit=limit, seed=seed))
    if not rows:
        raise ValueError("Không tìm thấy thế 15×15 nối 5 trong fixtures.")
    path = output / "alpha_beta.csv"
    _write_csv(path, rows)
    return path


def _tactical_positions(fixtures: Path, budget: int, seed: int) -> tuple[list[dict], list[dict]]:
    roots, pruning = [], []
    for item in json.loads(fixtures.read_text(encoding="utf-8")):
        rules = Rules(item["size"], item["connect"])
        state = GameState.from_moves(rules, item["moves"])
        expected = item["expected"]
        for name, policy in ROLLOUTS.items():
            mcts = MCTSAgent(budget, rollout=policy(), radius=2)
            result = mcts.choose_move(state, Random(seed))
            stats = {child.move: child for child in result.root}
            by_visits, by_mean = stats[result.max_visits], stats[result.max_mean]
            roots.append({
                "position": item["id"], "goal": item["goal"], "size": rules.size, "rollout": name,
                "seed": seed, "c": mcts.exploration, "iterations": budget,
                "max_visits_move": by_visits.move, "max_visits_n": by_visits.visits,
                "max_visits_mean": by_visits.mean, "max_visits_correct": by_visits.move in expected,
                "max_mean_move": by_mean.move, "max_mean_n": by_mean.visits,
                "max_mean_mean": by_mean.mean, "max_mean_correct": by_mean.move in expected,
                "different": by_visits.move != by_mean.move, "expected": json.dumps(expected),
            })
        if rules.size > 3:
            pruning.extend(_compare_pruning(item, state, depth=2, radius=2, limit=8, seed=seed))
    return roots, pruning


def run_benchmark(
    config: dict, profile: str, output: Path, fixtures: Path,
    opponent_override: str | None = None, notify: Callable[[str], None] = print,
) -> dict[str, Path]:
    spec = config["opponent"]
    name = opponent_override or spec["kind"]
    if name == "minimax":
        opponent = MinimaxAgent(spec["depth"], True, spec["radius"], spec["candidate_limit"])
    elif name == "random":
        opponent = RandomAgent()
    else:
        raise ValueError(f"Đối thủ chưa được hỗ trợ: {name}")
    games, moves = _paired_games(config, profile, opponent, name, notify)
    roots, pruning = _tactical_positions(fixtures, config[profile]["tactical_iterations"], config[profile]["seeds"][0])
    datasets = {"games": games, "moves": moves, "tactics": roots, "alpha_beta": pruning}
    paths = {key: output / f"{key}.csv" for key in datasets}
    for key, records in datasets.items():
        _write_csv(paths[key], records)
    return paths
