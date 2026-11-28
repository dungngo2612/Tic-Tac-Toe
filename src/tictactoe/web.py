"""Local HTTP server for the browser game."""

import json
import webbrowser
from dataclasses import asdict
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

from .ai.agent import Agent
from .ai.minimax import MinimaxAgent
from .cli import AGENT_NAMES, create_agent
from .config import read_config
from .game.match import turn_rng
from .game.rules import Rules
from .game.state import O, X, GameState

ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/game.js": ("game.js", "text/javascript; charset=utf-8"),
    "/caro-board.webp": ("caro-board.webp", "image/webp"),
}

DIFFICULTIES = ("easy", "medium", "hard")

HARD_DEFAULTS = {"depth": 10, "radius": 2, "candidate_limit": 12, "seconds": 1.5, "forcing_plies": 6}


def hard_agent(config_path: Path | None = None) -> MinimaxAgent:
    path = config_path or Path("configs/game.toml")
    overrides = read_config(path).get("hard", {}) if config_path or path.is_file() else {}
    if not isinstance(overrides, dict) or overrides.keys() - HARD_DEFAULTS.keys():
        raise ValueError("Cấu hình [hard] chứa tùy chọn không hợp lệ.")
    settings = HARD_DEFAULTS | overrides
    return MinimaxAgent(**settings)


def _setting(data: dict, key: str, allowed: tuple, default):
    value = data.get(key, default)
    if value not in allowed:
        raise ValueError(f"Giá trị không hợp lệ: {key}.")
    return value


def _preset_agent(difficulty: str, rules: Rules, hard: MinimaxAgent | None) -> Agent:
    if difficulty == "easy":
        return create_agent("random", rules)
    if difficulty == "medium":
        return create_agent("mcts", rules, iterations=60 if rules.size == 3 else 100, tactical=True)
    if rules.size == 3:
        return MinimaxAgent()
    return hard if hard is not None else hard_agent()


def _demo_agent(data: dict, rules: Rules) -> Agent:
    name = _setting(data, "agent", AGENT_NAMES[1:], "minimax")
    iterations = _setting(data, "iterations", (30, 60, 100, 200, 300, 600), 100)
    depth = _setting(data, "depth", (1, 2, 3), 2)
    c = _setting(data, "c", (0.5, 1, 1.4, 2), 1.4)
    if type(iterations) is not int or type(depth) is not int or type(c) not in (int, float):
        raise ValueError("Ngân sách tìm kiếm không hợp lệ.")
    rollout = _setting(data, "rollout", ("random", "heuristic"), "random")
    policy = _setting(data, "policy", ("max_visits", "max_mean"), "max_visits")
    tactical = data.get("tactical", False)
    if type(tactical) is not bool:
        raise ValueError("Tùy chọn chiến thuật không hợp lệ.")
    return create_agent(
        name, rules, iterations=iterations, depth=depth, c=c,
        rollout=rollout, policy=policy, tactical=tactical and rules.size == 15,
    )


def game_response(data: dict, *, hard: MinimaxAgent | None = None) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Dữ liệu ván đấu phải là một đối tượng.")
    size = _setting(data, "size", (3, 15), 3)
    if type(size) is not int:
        raise ValueError("Kích thước bàn không hợp lệ.")
    rules = Rules(size, 3 if size == 3 else 5)
    moves = data.get("moves", [])
    if not isinstance(moves, list) or len(moves) > rules.cells:
        raise ValueError("Danh sách nước đi không hợp lệ.")
    state = GameState.from_moves(rules, moves)
    action = _setting(data, "action", ("state", "ai"), "state")
    result = None
    if action == "ai":
        human = _setting(data, "human", (X, O), X)
        if type(human) is not int or state.outcome is not None or state.turn == human:
            raise ValueError("AI chỉ được đi trong lượt của mình.")
        seed = data.get("seed", 0)
        if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
            raise ValueError("Seed phải là số nguyên trong khoảng từ 0 đến 2³² − 1.")
        if "difficulty" in data:
            difficulty = _setting(data, "difficulty", DIFFICULTIES, "medium")
            agent = _preset_agent(difficulty, rules, hard)
        else:
            agent = _demo_agent(data, rules)
        result = agent.choose_move(state, turn_rng(seed, state))
        state = state.apply_move(result.move)
    return {"state": asdict(state), "search": asdict(result) if result is not None else None}


class GameHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, hard: MinimaxAgent):
        self.hard = hard
        super().__init__(*args)

    def _write(self, status: HTTPStatus, content: bytes, kind: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self) -> None:
        item = ASSETS.get(urlsplit(self.path).path)
        if item is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        name, kind = item
        content = files("tictactoe").joinpath("web_assets", name).read_bytes()
        self._write(HTTPStatus.OK, content, kind)

    def do_POST(self) -> None:
        if self.path != "/api/game":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        host = self.headers.get("Host")
        port = self.server.server_port
        if host not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{host}":
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if self.headers.get_content_type() != "application/json" or not 0 < length <= 8192:
                raise ValueError("Yêu cầu phải chứa JSON hợp lệ.")
            data = json.loads(self.rfile.read(length))
            response = game_response(data, hard=self.hard)
            status = HTTPStatus.OK
        except ValueError as error:
            status = HTTPStatus.BAD_REQUEST
            response = {"error": str(error)}
        self._write(status, json.dumps(response, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def log_request(self, code="-", size="-"):
        if code not in (HTTPStatus.OK, HTTPStatus.NOT_MODIFIED):
            super().log_request(code, size)


def serve(port: int, open_browser: bool = False, config_path: Path | None = None) -> None:
    handler = partial(GameHandler, hard=hard_agent(config_path))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"Mở {url} để chơi. Nhấn Ctrl+C để dừng.", flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nĐã dừng máy chủ.")
