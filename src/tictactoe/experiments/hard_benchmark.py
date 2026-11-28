"""Paired comparison of the current and previous web Hard presets."""

import argparse
import json
import platform
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from statistics import median, quantiles

from ..ai.minimax import MinimaxAgent
from ..cli import coordinate
from ..game.match import play_match
from ..game.rules import Rules
from ..game.state import O, SYMBOLS, X
from ..web import hard_agent

OPENINGS = (
    (112, 113),
    (112, 96, 98, 126),
    (112, 96, 111, 127),
    (112, 127, 98, 111),
)


def run(output: Path, config: Path | None = None) -> None:
    rules = Rules()
    old = MinimaxAgent(depth=4, candidate_limit=10, prioritize_forks=True)
    new = hard_agent(config)
    games = []
    for pair, opening in enumerate(OPENINGS, start=1):
        for new_side in (X, O):
            x, o = (new, old) if new_side == X else (old, new)
            state, searches = play_match(rules, x, o, opening=opening, seed=7)
            turns = []
            for index, search in enumerate(searches, start=len(opening)):
                side = X if index % 2 == 0 else O
                turns.append({
                    "move": search.move,
                    "coordinate": coordinate(search.move, rules.size),
                    "agent": "new" if side == new_side else "old",
                    "side": SYMBOLS[side],
                    "seconds": search.elapsed,
                    "completed_depth": search.completed_depth if side == new_side else 4,
                    "timed_out": search.timed_out,
                    "reason": search.reason,
                })
            result = {X: "win", 0: "draw", O: "loss"}[state.outcome * new_side]
            games.append({
                "pair": pair, "opening": list(opening), "new_side": SYMBOLS[new_side],
                "result": result, "winner": SYMBOLS[state.outcome], "turns": turns,
            })
            print(f"Cặp {pair}, bản mới cầm {SYMBOLS[new_side]}: {result} sau {state.ply} nước.", flush=True)
    timing = {}
    for name in ("new", "old"):
        turns = [turn for game in games for turn in game["turns"] if turn["agent"] == name]
        times = [turn["seconds"] for turn in turns]
        timing[name] = {
            "turns": len(times), "median_seconds": median(times),
            "p95_seconds": quantiles(times, n=100, method="inclusive")[94],
            "max_seconds": max(times), "timed_out": sum(turn["timed_out"] for turn in turns),
        }
    counts = Counter(game["result"] for game in games)
    summary = {
        "python": platform.python_version(),
        "rules": asdict(rules), "seed": 7, "old": asdict(old), "new": asdict(new),
        "results": {result: counts[result] for result in ("win", "draw", "loss")},
        "timing": timing, "games": games,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(summary["results"], timing)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/raw/hard/paired.json"))
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    run(args.output, args.config)
