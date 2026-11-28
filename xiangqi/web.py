"""Local graphical Xiangqi. Run from the project root: python3 -m xiangqi.web."""
import argparse
import json
import secrets
import threading
import webbrowser
from dataclasses import asdict
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .engine import Position
from .agents import choose as choose_ai

ASSETS = Path(__file__).parent / 'web_assets'


class Game:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset('ai', 1, 'medium')

    def reset(self, mode, human, difficulty, agent='minimax'):
        self.mode, self.human, self.difficulty = mode, human, difficulty
        self.agent = agent
        self.positions = [Position.initial()]
        self.moves = []
        self.analysis = None
        self.revision = secrets.token_hex(8)

    @property
    def position(self):
        return self.positions[-1]

    def result(self):
        legal = self.position.legal()
        winner = -self.position.turn if not legal else None
        # Three repeated positions end this casual game in a draw.
        draw = winner is None and self.positions.count(self.position) >= 3
        return legal, winner, draw

    def push(self, move):
        piece, captured = self.position.board[move[0]], self.position.board[move[1]]
        self.positions.append(self.position.apply(move))
        self.moves.append({'from': move[0], 'to': move[1], 'piece': piece, 'captured': captured})
        self.revision = secrets.token_hex(8)

    def data(self):
        legal, winner, draw = self.result()
        return dict(board=self.position.board, turn=self.position.turn,
                    legal=[] if draw else legal, checked=self.position.checked(),
                    winner=winner, draw=draw, moves=self.moves, mode=self.mode,
                    human=self.human, difficulty=self.difficulty, revision=self.revision,
                    agent=self.agent, engine={'minimax': 'Minimax', 'mcts': 'MCTS', 'random': 'Ngẫu nhiên'}[self.agent],
                    analysis=self.analysis)


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address):
        super().__init__(address, Handler)
        self.games = {}
        self.games_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    cookie_name = 'xiangqi'
    cookie_path = '/'

    def reply(self, status, data, content_type='application/json; charset=utf-8', cookie=None):
        body = json.dumps(data, ensure_ascii=False).encode() if content_type.startswith('application/json') else data
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if cookie:
            self.send_header('Set-Cookie', f'{self.cookie_name}={cookie}; HttpOnly; SameSite=Strict; Path={self.cookie_path}')
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        port = self.server.server_port
        return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

    def game(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
        except Exception:
            pass
        token = cookie[self.cookie_name].value if self.cookie_name in cookie else None
        with self.server.games_lock:
            if token not in self.server.games:
                if len(self.server.games) >= 256:
                    raise ValueError('Đã đạt giới hạn phiên chơi. Hãy khởi động lại máy chủ.')
                token = secrets.token_urlsafe(24)
                self.server.games[token] = Game()
            return self.server.games[token], token

    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, {'error': 'Địa chỉ không hợp lệ.'})
        if self.path == '/api/state':
            try:
                game, token = self.game()
                with game.lock:
                    self.reply(200, game.data(), cookie=token)
            except ValueError as error:
                self.reply(503, {'error': str(error)})
            return
        assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                  '/style.css': ('style.css', 'text/css; charset=utf-8'),
                  '/app.js': ('app.js', 'text/javascript; charset=utf-8')}
        if self.path not in assets:
            return self.reply(404, {'error': 'Không tìm thấy.'})
        name, kind = assets[self.path]
        self.reply(200, (ASSETS / name).read_bytes(), kind)

    def do_POST(self):
        origin = self.headers.get('Origin')
        if not self.valid_host() or (origin and origin != 'http://' + self.headers.get('Host', '')):
            return self.reply(403, {'error': 'Yêu cầu không hợp lệ.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                raise ValueError('Dữ liệu yêu cầu không hợp lệ.')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('Dữ liệu yêu cầu không hợp lệ.')
            game, token = self.game()
            with game.lock:
                if self.path == '/api/new':
                    mode, human, difficulty = payload.get('mode'), payload.get('human'), payload.get('difficulty')
                    agent = payload.get('agent', 'minimax')
                    if mode not in ('ai', 'local') or type(human) is not int or human not in (-1, 1) or difficulty not in ('easy', 'medium', 'hard'):
                        raise ValueError('Thiết lập ván chơi không hợp lệ.')
                    if agent not in ('minimax', 'mcts', 'random'):
                        raise ValueError('Thuật toán không hợp lệ.')
                    game.reset(mode, human, difficulty, agent)
                else:
                    if payload.get('revision') != game.revision:
                        raise ValueError('Ván cờ đã thay đổi. Hãy tải lại trang.')
                    legal, winner, draw = game.result()
                    if self.path == '/api/undo':
                        count = 2 if game.mode == 'ai' and game.position.turn == game.human else 1
                        count = min(count, len(game.moves))
                        if count:
                            del game.positions[-count:]
                            del game.moves[-count:]
                            game.revision = secrets.token_hex(8)
                            game.analysis = None
                    elif self.path in ('/api/move', '/api/ai'):
                        if winner or draw:
                            raise ValueError('Ván cờ đã kết thúc.')
                        ai_turn = game.mode == 'ai' and game.position.turn != game.human
                        if self.path == '/api/ai':
                            if not ai_turn:
                                raise ValueError('Chưa đến lượt máy.')
                            move, analysis = choose_ai(game.position, game.agent, game.difficulty,
                                                       seed=7 + len(game.moves))
                            game.analysis = asdict(analysis)
                        else:
                            move = payload.get('move')
                            if ai_turn or not isinstance(move, list) or len(move) != 2 or any(type(x) is not int for x in move):
                                raise ValueError('Nước đi không hợp lệ.')
                            move = tuple(move)
                            if move not in legal:
                                raise ValueError('Nước đi không hợp lệ.')
                        game.push(move)
                    else:
                        return self.reply(404, {'error': 'Không tìm thấy.'})
                self.reply(200, game.data(), cookie=token)
        except (ValueError, TypeError) as error:
            self.reply(400, {'error': str(error)})


def main():
    parser = argparse.ArgumentParser(description='Cờ Tướng · Giao diện web')
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    with Server(('127.0.0.1', args.port)) as server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print(f'Cờ Tướng đang chạy tại {url} · Ctrl+C để dừng.', flush=True)
        if args.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
