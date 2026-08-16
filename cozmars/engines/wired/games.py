"""Python board games — surface /api/mods/{Name}/ giống WireOS."""

from __future__ import annotations

import random
from typing import Any, Dict, List


class TicTacToe:
    name = "TicTacToe"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> dict:
        self.board = [" "] * 9
        self.turn = "X"
        self.winner = ""
        self.status = "play"
        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "board": [self.board[i : i + 3] for i in range(0, 9, 3)],
            "turn": self.turn,
            "status": self.status,
            "winner": self.winner,
            "youAre": "X",
            "botIs": "O",
            "message": self.status,
        }

    def summary(self) -> str:
        return f"Caro 3x3 lượt {self.turn} {self.status}"

    def play_uci(self, uci: str) -> dict:
        try:
            i = int(uci)
        except ValueError:
            # "a1" style
            i = 0
            if len(uci) >= 2:
                i = (ord(uci[0]) - 97) + (3 - int(uci[1])) * 3
        if not 0 <= i < 9 or self.board[i] != " " or self.status != "play":
            raise ValueError("illegal")
        self.board[i] = "X"
        self._endcheck()
        if self.status == "play":
            empties = [k for k, c in enumerate(self.board) if c == " "]
            if empties:
                self.board[random.choice(empties)] = "O"
                self._endcheck()
        return self.snapshot()

    def legal(self) -> List[str]:
        return [str(i) for i, c in enumerate(self.board) if c == " "]

    def _endcheck(self) -> None:
        lines = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
        for a, b, c in lines:
            if self.board[a] != " " and self.board[a] == self.board[b] == self.board[c]:
                self.winner = self.board[a]
                self.status = "win"
                return
        if all(c != " " for c in self.board):
            self.status = "draw"


class G2048:
    name = "G2048"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> dict:
        self.grid = [[0] * 4 for _ in range(4)]
        self._spawn()
        self._spawn()
        self.status = "play"
        return self.snapshot()

    def snapshot(self) -> dict:
        return {"board": self.grid, "status": self.status, "turn": "player"}

    def summary(self) -> str:
        return f"2048 max {max(max(r) for r in self.grid)}"

    def play_uci(self, uci: str) -> dict:
        d = {"u": "up", "d": "down", "l": "left", "r": "right"}.get(uci[:1].lower(), uci)
        old = [row[:] for row in self.grid]
        self._move(d)
        if self.grid != old:
            self._spawn()
        return self.snapshot()

    def legal(self) -> List[str]:
        return ["u", "d", "l", "r"]

    def _spawn(self) -> None:
        empty = [(r, c) for r in range(4) for c in range(4) if self.grid[r][c] == 0]
        if not empty:
            self.status = "lose"
            return
        r, c = random.choice(empty)
        self.grid[r][c] = 4 if random.random() < 0.1 else 2

    def _move(self, d: str) -> None:
        def line(vals):
            tiles = [v for v in vals if v]
            out = []
            i = 0
            while i < len(tiles):
                if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
                    out.append(tiles[i] * 2)
                    i += 2
                else:
                    out.append(tiles[i])
                    i += 1
            return out + [0] * (4 - len(out))

        g = self.grid
        if d == "left":
            self.grid = [line(r) for r in g]
        elif d == "right":
            self.grid = [list(reversed(line(list(reversed(r))))) for r in g]
        elif d == "up":
            cols = [[g[r][c] for r in range(4)] for c in range(4)]
            cols = [line(c) for c in cols]
            self.grid = [[cols[c][r] for c in range(4)] for r in range(4)]
        elif d == "down":
            cols = [[g[r][c] for r in range(4)] for c in range(4)]
            cols = [list(reversed(line(list(reversed(c))))) for c in cols]
            self.grid = [[cols[c][r] for c in range(4)] for r in range(4)]


class ChessDummy:
    name = "Chess"
    START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> dict:
        self.fen = self.START
        self.status = "play"
        self.history: list[str] = []
        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "fen": self.fen,
            "board": self._rows(),
            "turn": "white",
            "status": self.status,
            "winner": "",
            "lastMove": self.history[-1] if self.history else "",
            "history": self.history,
            "youAre": "white",
            "botIs": "black",
            "message": "python-chess optional — placeholder FEN",
        }

    def summary(self) -> str:
        return "Cờ vua (engine Python tối giản / FEN start)."

    def play_uci(self, uci: str) -> dict:
        self.history.append(uci)
        return self.snapshot()

    def legal(self) -> List[str]:
        return []

    def _rows(self) -> list:
        rows = []
        for part in self.fen.split()[0].split("/"):
            row = []
            for ch in part:
                if ch.isdigit():
                    row.extend(["."] * int(ch))
                else:
                    row.append(ch)
            rows.append(row)
        return rows


GAMES = {
    "TicTacToe": TicTacToe(),
    "G2048": G2048(),
    "Chess": ChessDummy(),
    "Caro": TicTacToe(),
}


def handle(name: str, path: str, uci: str = "", level: str = "") -> Dict[str, Any]:
    g = GAMES.get(name) or GAMES["TicTacToe"]
    if path in ("new",):
        return g.reset()
    if path in ("state", ""):
        return g.snapshot()
    if path == "summary":
        return {"text": g.summary()}
    if path == "move":
        return g.play_uci(uci)
    if path == "legal":
        return {"moves": g.legal()}
    if path == "exit":
        g.reset()
        return {"status": "ok", "game": name}
    if path in ("comment", "comment_mode", "difficulty"):
        return {
            "comment": True,
            "commentMode": "google_vi",
            "xiaozhiAvailable": False,
            "googleVIAvailable": True,
            "googleLang": "vi",
            "difficulty": level or "normal",
        }
    return g.snapshot()
