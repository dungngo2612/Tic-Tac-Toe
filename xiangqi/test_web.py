"""Run with: python3 -m unittest xiangqi.test_web -v."""
import http.client
import json
import threading
import unittest

from .engine import Position, choose_move, side
from .web import Server


def position(pieces, turn=1):
    board = [''] * 90
    for (r, c), piece in pieces.items():
        board[r * 9 + c] = piece
    return Position(tuple(board), turn)


class RulesTests(unittest.TestCase):
    def test_initial_and_pawns(self):
        state = Position.initial()
        self.assertEqual(sum(bool(p) for p in state.board), 32)
        self.assertEqual(len(state.legal()), 44)
        self.assertIn((54, 45), state.legal())
        self.assertNotIn((54, 55), state.legal())
        self.assertIn((27, 36), Position(state.board, -1).legal())
        state = position({(9, 4): 'K', (0, 3): 'k', (4, 0): 'P'})
        self.assertIn((36, 37), state.legal())
        self.assertNotIn((36, 45), state.legal())

    def test_horse_leg_and_elephant_eye(self):
        state = position({(9, 4): 'K', (0, 3): 'k', (7, 1): 'H', (6, 1): 'P', (9, 2): 'E', (8, 3): 'A'})
        self.assertNotIn((64, 45), state.legal())
        self.assertIn((64, 57), state.legal())
        self.assertNotIn((83, 67), state.legal())
        self.assertIn((83, 63), state.legal())
        state = position({(9, 4): 'K', (0, 3): 'k', (5, 2): 'E'})
        self.assertNotIn((47, 31), state.legal())

    def test_cannon_requires_one_screen(self):
        state = position({(9, 4): 'K', (0, 3): 'k', (7, 0): 'C', (5, 0): 'P', (2, 0): 'r'})
        self.assertIn((63, 18), state.legal())
        self.assertNotIn((63, 36), state.legal())
        self.assertIn((63, 54), state.legal())
        state = position({(9, 4): 'K', (0, 3): 'k', (7, 0): 'C', (2, 0): 'r'})
        self.assertNotIn((63, 18), state.legal())

    def test_facing_generals_and_check(self):
        state = position({(9, 4): 'K', (0, 4): 'k', (5, 4): 'R'})
        self.assertNotIn((49, 48), state.legal())
        self.assertFalse(state.checked())
        state = position({(9, 4): 'K', (0, 3): 'k', (5, 4): 'r', (8, 0): 'R'})
        self.assertTrue(state.checked())
        self.assertNotIn((72, 73), state.legal())
        self.assertNotIn((85, 75), state.legal())  # Tướng cannot move diagonally.

    def test_ai_returns_legal_moves_for_both_sides(self):
        state = Position.initial()
        for difficulty in ('easy', 'medium', 'hard'):
            move = choose_move(state, difficulty)
            self.assertIn(move, state.legal())
            state = state.apply(move)


class TacticsTests(unittest.TestCase):
    def test_does_not_trade_rook_for_a_defended_pawn_at_search_horizon(self):
        state = position({(9, 4): 'K', (0, 4): 'k', (5, 4): 'P',
                          (7, 0): 'R', (7, 3): 'p', (3, 3): 'r'})
        self.assertIn((63, 66), state.legal())
        # Material-only depth-one search eats the pawn and loses its rook.
        greedy = max(state.legal(), key=lambda m: -state.apply(m).score())
        self.assertEqual(greedy, (63, 66))
        move = choose_move(state, 'hard', seconds=2, max_depth=1)
        self.assertNotEqual(move, greedy)
        black = Position(tuple(p.swapcase() for p in reversed(state.board)), -1)
        self.assertNotEqual(choose_move(black, 'hard', seconds=2, max_depth=1), (26, 23))

    def test_takes_undefended_rook(self):
        state = position({(9, 4): 'K', (0, 4): 'k', (5, 4): 'P',
                          (7, 0): 'R', (7, 3): 'r'})
        self.assertEqual(choose_move(state, 'hard', seconds=2, max_depth=2), (63, 66))

    def test_wins_in_one_by_leaving_opponent_without_moves(self):
        state = position({(9, 4): 'K', (0, 4): 'k', (5, 4): 'P',
                          (2, 3): 'R', (1, 0): 'R'})
        move = choose_move(state, 'hard', seconds=2, max_depth=2)
        opponent = state.apply(move)
        # Xiangqi stalemate is a win as well as checkmate.
        self.assertEqual(opponent.legal(), [])

    def test_fast_check_matches_original_move_based_detection(self):
        from random import Random
        rng = Random(7)
        state = Position.initial()
        for _ in range(150):
            for team in (1, -1):
                king = 'K' if team == 1 else 'k'
                expected = king not in state.board or any(
                    end == state.board.index(king)
                    for start, piece in enumerate(state.board) if side(piece) == -team
                    for _, end in state.pseudo(start))
                self.assertEqual(state.checked(team), expected)
            moves = state.legal()
            state = state.apply(rng.choice(moves)) if moves else Position.initial()


class MCTSTests(unittest.TestCase):
    def test_reproducibility_and_visit_accounting(self):
        from .agents import mcts
        state = Position.initial()
        a, first = mcts(state, iterations=50, seconds=None, seed=42)
        b, second = mcts(state, iterations=50, seconds=None, seed=42)
        self.assertEqual(a, b)
        self.assertIn(a, state.legal())
        self.assertEqual(first.root, second.root)
        self.assertEqual(first.iterations, 50)
        self.assertEqual(sum(row['visits'] for row in first.root), 50)
        self.assertTrue(all(-1 <= row['mean'] <= 1 for row in first.root))

    def test_opponent_is_adversarial_not_cooperative(self):
        from .agents import mcts
        # Taking the bait is winning only if the opponent blunders. The safe
        # branch repeats for a draw. UCT must learn to prefer the safe branch.
        class ToyPosition:
            graph = {'root': [((0, 1), 'bait'), ((0, 2), 'safe')],
                     'bait': [((1, 3), 'loss'), ((1, 4), 'chance')],
                     'chance': [((4, 5), 'win')],
                     'safe': [((2, 6), 'return')], 'return': [((6, 2), 'safe')],
                     'loss': [], 'win': []}

            def __init__(self, name='root', turn=1):
                self.name, self.turn, self.board = name, turn, (name,)

            def legal(self):
                return [move for move, _ in self.graph[self.name]]

            def apply(self, move):
                return ToyPosition(dict(self.graph[self.name])[move], -self.turn)

            def score(self):
                return 0

        move, report = mcts(ToyPosition(), iterations=600, seconds=None, rollout_depth=6)
        self.assertEqual(move, (0, 2))
        self.assertEqual(sum(row['visits'] for row in report.root), 600)


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = Server(('127.0.0.1', 0))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.cookie = None

    def request(self, path, payload=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        headers = {'Content-Type': 'application/json'}
        if self.cookie:
            headers['Cookie'] = self.cookie
        conn.request('GET' if payload is None else 'POST', path,
                     None if payload is None else json.dumps(payload), headers)
        response = conn.getresponse()
        if response.getheader('Set-Cookie'):
            self.cookie = response.getheader('Set-Cookie').split(';')[0]
        body = response.read()
        status = response.status
        conn.close()
        return status, json.loads(body) if path.startswith('/api/') else body

    def test_page_and_move_ai_undo(self):
        self.assertEqual(self.request('/')[0], 200)
        status, state = self.request('/api/state')
        self.assertEqual(status, 200)
        payload = {'revision': state['revision'], 'move': [54, 45]}
        self.assertEqual(self.request('/api/move', {**payload, 'move': [54, 55]})[0], 400)
        status, moved = self.request('/api/move', payload)
        self.assertEqual(status, 200)
        self.assertEqual(moved['turn'], -1)
        self.assertEqual(self.request('/api/move', payload)[0], 400)
        status, moved = self.request('/api/ai', {'revision': moved['revision']})
        self.assertEqual(status, 200)
        self.assertEqual(len(moved['moves']), 2)
        self.assertEqual(moved['engine'], 'Minimax')
        self.assertEqual(moved['analysis']['name'], 'Minimax / Alpha-Beta')
        self.assertGreater(moved['analysis']['depth'], 0)
        _, undone = self.request('/api/undo', {'revision': moved['revision']})
        self.assertEqual(undone['board'], state['board'])
        self.assertEqual(undone['moves'], [])

    def test_black_local_sessions_and_payloads(self):
        _, state = self.request('/api/new', {'mode': 'ai', 'human': -1, 'difficulty': 'easy'})
        self.assertEqual(self.request('/api/move', {'revision': state['revision'], 'move': [54, 45]})[0], 400)
        _, state = self.request('/api/ai', {'revision': state['revision']})
        self.assertEqual(state['turn'], -1)
        _, state = self.request('/api/new', {'mode': 'local', 'human': 1, 'difficulty': 'easy'})
        for move in ([54, 45], [27, 36]):
            status, state = self.request('/api/move', {'revision': state['revision'], 'move': move})
            self.assertEqual(status, 200)
        cookie = self.cookie
        self.cookie = None
        _, separate = self.request('/api/state')
        self.assertEqual(separate['moves'], [])
        self.assertNotEqual(cookie, self.cookie)
        self.assertEqual(self.request('/api/new', [1, 2])[0], 400)

    def test_mcts_selection_and_unknown_algorithm(self):
        _, state = self.request('/api/new', {'mode': 'ai', 'human': -1, 'difficulty': 'easy', 'agent': 'mcts'})
        status, result = self.request('/api/ai', {'revision': state['revision']})
        self.assertEqual(status, 200)
        self.assertEqual(result['agent'], 'mcts')
        self.assertGreater(result['analysis']['iterations'], 0)
        self.assertEqual(sum(s['visits'] for s in result['analysis']['root']), result['analysis']['iterations'])
        status, _ = self.request('/api/new', {'mode': 'ai', 'human': -1, 'difficulty': 'easy', 'agent': 'invalid'})
        self.assertEqual(status, 400)

    def test_repetition_and_stalemate(self):
        from .web import Game
        game = Game()
        game.positions = [game.position] * 3
        self.assertTrue(game.data()['draw'])
        game.positions = [position({(0, 4): 'k', (2, 3): 'R', (1, 5): 'R', (9, 4): 'K', (5, 4): 'P'}, -1)]
        self.assertFalse(game.position.checked())
        self.assertEqual(game.data()['winner'], 1)


if __name__ == '__main__':
    unittest.main()
