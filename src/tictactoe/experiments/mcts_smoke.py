"""Small, seeded MCTS integration demo. Emit results as JSON on stdout."""

import json
from dataclasses import asdict
from platform import python_version
from random import Random

from ..ai.mcts import MCTSAgent, select_root
from ..ai.rollout import HeuristicRollout, RandomRollout
from ..cli import coordinate
from ..game import CLASSIC_RULES, GameState, Rules
from ..game.match import play_match


def main() -> None:
    seed = 7
    policies = {"random": RandomRollout(), "heuristic": HeuristicRollout()}
    agents = {name: MCTSAgent(100, 1.4, policy, radius=2) for name, policy in policies.items()}
    final, decisions = play_match(CLASSIC_RULES, agents["random"], agents["heuristic"], seed=seed)
    sample = {
        "python": python_version(), "seed": seed, "iterations_per_move": 100, "c": 1.4,
        "policy": "max_visits", "tactical": False, "guarded": False,
        "game_3x3": {
            "connect": 3, "X": "random", "O": "heuristic", "outcome": final.outcome,
            "moves": [coordinate(d.move, 3) for d in decisions],
            "iterations": sum(d.iterations for d in decisions), "rollouts": sum(d.rollouts for d in decisions),
        },
        "probes_15x15": [],
    }

    for moves in ([], [112, 113, 97, 128], [108, 109, 0, 110, 2, 111, 4, 112]):
        state = GameState.from_moves(Rules(15, 5), moves)
        for name, agent in agents.items():
            result = agent.choose_move(state, Random(seed))
            selected = next(child for child in result.root if child.move == result.move)
            sample["probes_15x15"].append({
                "opening": moves, "connect": 5, "radius": agent.radius, "rollout": name,
                "selected": coordinate(result.move, 15), "iterations": result.iterations,
                "rollouts": result.rollouts, "root_moves_visited": len(result.root),
                "selected_stats": asdict(selected), "elapsed_seconds": result.elapsed,
            })

    state = GameState.from_moves(CLASSIC_RULES, [0, 4, 8])
    result = agents["random"].choose_move(state, Random(seed))
    sample["same_tree_3x3"] = {
        "opening": [0, 4, 8], "rollout": "random",
        "max_visits": asdict(select_root(result.root, "max_visits")),
        "max_mean": asdict(select_root(result.root, "max_mean")),
    }
    print(json.dumps(sample, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
