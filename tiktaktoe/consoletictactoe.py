from typing import List, Optional, Tuple
import random


class GameQuit(Exception):
    """Raised when the player chooses to quit the game."""


def print_board(board: List[str]) -> None:
    cells = [c if c != " " else str(i + 1) for i, c in enumerate(board)]
    print("\n")
    print(f" {cells[0]} | {cells[1]} | {cells[2]} ")
    print("---+---+---")
    print(f" {cells[3]} | {cells[4]} | {cells[5]} ")
    print("---+---+---")
    print(f" {cells[6]} | {cells[7]} | {cells[8]} ")
    print("\n")


def winning_lines() -> List[Tuple[int, int, int]]:
    return [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    ]


def check_winner(board: List[str]) -> Optional[str]:
    for a, b, c in winning_lines():
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a]
    return None


def is_draw(board: List[str]) -> bool:
    return all(cell != " " for cell in board)


def prompt_move(board: List[str], player: str) -> int:
    while True:
        raw = input(
            f"Player {player}, choose a position (1-9, or 'q' to quit): "
        ).strip().lower()

        if raw in {"q", "quit", "exit"}:
            raise GameQuit

        try:
            pos = int(raw)
        except ValueError:
            print("Please enter a number from 1 to 9.")
            continue

        if not 1 <= pos <= 9:
            print("Position must be between 1 and 9.")
            continue

        idx = pos - 1
        if board[idx] != " ":
            print("That spot is already taken. Choose another.")
            continue

        return idx


def prompt_mode() -> str:
    """Ask the user which mode they want to play in.

    Returns "pvp" for player-vs-player or "cpu" for player-vs-CPU.
    Can raise GameQuit if the user chooses to quit.
    """

    while True:
        raw = input(
            "Choose mode: 1) Player vs Player  2) Player vs CPU  (or 'q' to quit): "
        ).strip().lower()

        if raw in {"q", "quit", "exit"}:
            raise GameQuit

        if raw in {"1", "pvp", "player vs player"}:
            return "pvp"
        if raw in {"2", "cpu", "vs cpu", "pvc"}:
            return "cpu"

        print("Please enter 1, 2, or 'q' to quit.")


def prompt_difficulty() -> str:
    """Ask the user for CPU difficulty level: easy, medium, or hard.

    Returns one of "easy", "medium", "hard". Can raise GameQuit.
    """

    while True:
        raw = input(
            "Choose CPU difficulty: 1) Easy  2) Medium  3) Hard  (or 'q' to quit): "
        ).strip().lower()

        if raw in {"q", "quit", "exit"}:
            raise GameQuit

        if raw in {"1", "easy", "e"}:
            return "easy"
        if raw in {"2", "medium", "m", "normal"}:
            return "medium"
        if raw in {"3", "hard", "h", "difficult", "d"}:
            return "hard"

        print("Please enter 1, 2, 3, or 'q' to quit.")


def _available_moves(board: List[str]) -> List[int]:
    return [i for i, c in enumerate(board) if c == " "]


def _find_winning_move(board: List[str], symbol: str) -> Optional[int]:
    """Return an index where `symbol` can move to win immediately, or None."""

    for idx in _available_moves(board):
        board[idx] = symbol
        if check_winner(board) == symbol:
            board[idx] = " "
            return idx
        board[idx] = " "
    return None


def _cpu_move_easy(board: List[str]) -> int:
    """Easy CPU: pure random among available moves."""

    available = _available_moves(board)
    if not available:
        raise RuntimeError("No available moves for CPU.")
    return random.choice(available)


def _cpu_move_medium(board: List[str], cpu_symbol: str, human_symbol: str) -> int:
    """Medium CPU: try to win, then block, otherwise random."""

    # 1) Can CPU win this turn?
    win_move = _find_winning_move(board, cpu_symbol)
    if win_move is not None:
        return win_move

    # 2) Can human win next turn? Block them.
    block_move = _find_winning_move(board, human_symbol)
    if block_move is not None:
        return block_move

    # 3) Otherwise random.
    return _cpu_move_easy(board)


def _minimax(
    board: List[str],
    current: str,
    cpu_symbol: str,
    human_symbol: str,
) -> Tuple[int, Optional[int]]:
    """Minimax algorithm: returns (score, move).

    Score is from CPU perspective: +1 win, -1 loss, 0 draw.
    """

    winner = check_winner(board)
    if winner == cpu_symbol:
        return 1, None
    if winner == human_symbol:
        return -1, None
    if is_draw(board):
        return 0, None

    best_move: Optional[int] = None

    if current == cpu_symbol:
        best_score = -999
        for idx in _available_moves(board):
            board[idx] = cpu_symbol
            score, _ = _minimax(board, human_symbol, cpu_symbol, human_symbol)
            board[idx] = " "
            if score > best_score:
                best_score = score
                best_move = idx
    else:
        best_score = 999
        for idx in _available_moves(board):
            board[idx] = human_symbol
            score, _ = _minimax(board, cpu_symbol, cpu_symbol, human_symbol)
            board[idx] = " "
            if score < best_score:
                best_score = score
                best_move = idx

    return best_score, best_move


def _cpu_move_hard(board: List[str], cpu_symbol: str, human_symbol: str) -> int:
    """Hard CPU: optimal play via minimax (unbeatable)."""

    _, move = _minimax(board, cpu_symbol, cpu_symbol, human_symbol)
    if move is None:
        # Fallback: choose any available move (shouldn't normally happen).
        return _cpu_move_easy(board)
    return move


def cpu_move(board: List[str], difficulty: str, cpu_symbol: str, human_symbol: str) -> int:
    """Choose a move for the CPU based on difficulty level."""

    if difficulty == "easy":
        return _cpu_move_easy(board)
    if difficulty == "medium":
        return _cpu_move_medium(board, cpu_symbol, human_symbol)
    # default and "hard"
    return _cpu_move_hard(board, cpu_symbol, human_symbol)


def play_single_game() -> None:
    """Play a single game (one round) of tic-tac-toe."""

    mode = prompt_mode()
    vs_cpu = mode == "cpu"

    board = [" "] * 9
    current = "X"
    human_symbol = "X"
    cpu_symbol = "O"
    difficulty = "easy"

    if vs_cpu:
        difficulty = prompt_difficulty()
        print(f"You are {human_symbol}. CPU is {cpu_symbol}. Difficulty: {difficulty}.")

    print("\nEnter positions 1-9 as shown on the board.\n")

    while True:
        print_board(board)

        if vs_cpu and current == cpu_symbol:
            move = cpu_move(board, difficulty, cpu_symbol, human_symbol)
            print(f"CPU ({cpu_symbol}) chooses position {move + 1}")
        else:
            move = prompt_move(board, current)

        board[move] = current

        winner = check_winner(board)
        if winner:
            print_board(board)
            if vs_cpu and winner == cpu_symbol:
                print("CPU wins!")
            elif vs_cpu and winner == human_symbol:
                print("You win!")
            else:
                print(f"Player {winner} wins!")
            break

        if is_draw(board):
            print_board(board)
            print("It's a draw!")
            break

        current = "O" if current == "X" else "X"


def play() -> None:
    print("Tic-Tac-Toe (Console)")

    while True:
        try:
            play_single_game()
        except GameQuit:
            print("\nGame quit. Goodbye!")
            return

        again = input("Play again? (y/n, or 'q' to quit): ").strip().lower()
        if again in {"q", "quit", "exit"}:
            print("Goodbye!")
            return
        if again in {"n", "no"}:
            print("Returning to main menu...\n")
            # Loop restarts; user will see the mode selection again.
            continue
        # For 'y' or anything else, just start another game (mode is chosen inside play_single_game).


if __name__ == "__main__":
    play()