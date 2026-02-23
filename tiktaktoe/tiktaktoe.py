import tkinter as tk
from tkinter import messagebox
import random
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

try:
    from PIL import Image, ImageTk
except ImportError:  # Pillow is optional; app still runs without scaling
    Image = None
    ImageTk = None


# ----------------------------
# Game logic helpers
# ----------------------------

WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 4, 6),  # cols
    (0, 4, 8), (2, 4, 6)              # diags
]


def winner_of(board: List[str]) -> Optional[str]:
    for a, b, c in WIN_LINES:
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a]
    return None


def is_draw(board: List[str]) -> bool:
    return winner_of(board) is None and all(cell != " " for cell in board)


def available_moves(board: List[str]) -> List[int]:
    return [i for i, v in enumerate(board) if v == " "]


def minimax(board: List[str], current: str, cpu: str, human: str) -> Tuple[int, Optional[int]]:
    w = winner_of(board)
    if w == cpu:
        return 1, None
    if w == human:
        return -1, None
    if is_draw(board):
        return 0, None

    moves = available_moves(board)

    if current == cpu:
        best_score = -10
        best_move = None
        for m in moves:
            board[m] = cpu
            score, _ = minimax(board, human, cpu, human)
            board[m] = " "
            if score > best_score:
                best_score = score
                best_move = m
        return best_score, best_move
    else:
        best_score = 10
        best_move = None
        for m in moves:
            board[m] = human
            score, _ = minimax(board, cpu, cpu, human)
            board[m] = " "
            if score < best_score:
                best_score = score
                best_move = m
        return best_score, best_move


def find_winning_move(board: List[str], player: str) -> Optional[int]:
    for m in available_moves(board):
        board[m] = player
        if winner_of(board) == player:
            board[m] = " "
            return m
        board[m] = " "
    return None


def pick_cpu_move(board: List[str], difficulty: str, cpu: str, human: str) -> int:
    moves = available_moves(board)

    if difficulty == "Easy":
        return random.choice(moves)

    if difficulty == "Medium":
        m = find_winning_move(board, cpu)
        if m is not None:
            return m

        m = find_winning_move(board, human)
        if m is not None:
            return m

        center = [4] if 4 in moves else []
        corners = [i for i in (0, 2, 6, 8) if i in moves]
        edges = [i for i in (1, 3, 5, 7) if i in moves]

        weighted = []
        weighted += center * 5
        weighted += corners * 3
        weighted += edges * 1

        if random.random() < 0.25:
            return random.choice(moves)
        return random.choice(weighted if weighted else moves)

    _, m = minimax(board, cpu, cpu, human)
    return m if m is not None else random.choice(moves)


# ----------------------------
# UI / App
# ----------------------------

@dataclass
class GameConfig:
    mode: str
    cpu_difficulty: str
    human_symbol: str = "X"


class TicTacToeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tic Tac Toe")
        self.resizable(False, False)

        # Fixed window size (about 3in x 5in, based on screen DPI)
        self.WINDOW_WIDTH = self._inches_to_pixels(5.0)
        self.WINDOW_HEIGHT = self._inches_to_pixels(3.0)
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.config_data: Optional[GameConfig] = None
        self.board: List[str] = [" "] * 9
        self.current_player: str = "X"
        self.game_over: bool = False

        self.menu_frame = tk.Frame(self)
        # Game frame uses default background; ack.png is drawn behind the widgets.
        # If the image fails to load, it will fall back to the standard Tk color.
        self.game_frame = tk.Frame(self, padx=18, pady=18)

        # Menu image refs
        self.menu_bg_img: Optional[tk.PhotoImage] = None
        self.menu_bg_label: Optional[tk.Label] = None
        self.menu_bg_path: Optional[str] = None

        # Game background image refs (NEW)
        self.game_bg_img: Optional[tk.PhotoImage] = None
        self.game_bg_label: Optional[tk.Label] = None
        self.game_bg_path: Optional[str] = None

        self._build_menu()
        self._build_game()
        self._show_menu()

    # ---------------- Inches to pixels ----------------

    def _inches_to_pixels(self, inches: float) -> int:
        ppi = self.winfo_fpixels("1i")
        return int(round(inches * ppi))

    # ---------------- Menu background ----------------

    def _set_menu_background_5in(self, png_path: str):
        self.menu_bg_path = png_path

        if self.menu_bg_label is None:
            self.menu_bg_label = tk.Label(self.menu_frame, borderwidth=0, highlightthickness=0)
            self.menu_bg_label.place(relx=0.5, rely=0.58, anchor="center")

        target = self._inches_to_pixels(5.0)

        try:
            if Image is not None and ImageTk is not None:
                img = Image.open(png_path).convert("RGBA")
                img = img.resize((target, target), Image.LANCZOS)
                self.menu_bg_img = ImageTk.PhotoImage(img)
            else:
                self.menu_bg_img = tk.PhotoImage(file=png_path)

            self.menu_bg_label.config(image=self.menu_bg_img)
            self.menu_bg_label.lower()
        except (tk.TclError, FileNotFoundError, OSError):
            self.menu_bg_img = None
            self.menu_bg_label.config(image="")

    # ---------------- Game background (NEW) ----------------

    @staticmethod
    def _fit_image_cover(img, target_w: int, target_h: int):
        """
        Preserve aspect ratio and fit the entire image inside the
        target area without cropping (letterbox if needed).
        Requires Pillow.
        """
        iw, ih = img.size
        if iw == 0 or ih == 0:
            return img

        # Scale so the whole image fits within target bounds
        scale = min(target_w / iw, target_h / ih)
        new_w = int(iw * scale)
        new_h = int(ih * scale)

        resized = img.resize((new_w, new_h), Image.LANCZOS)

        # Paste onto a transparent canvas the size of the target, centered
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        left = (target_w - new_w) // 2
        top = (target_h - new_h) // 2
        canvas.paste(resized, (left, top))
        return canvas

    def set_game_background(self, filename: str):
        """
        PUBLIC helper you can use to set a background on the game screen.

        Usage:
            self.set_game_background("my_game_bg.png")

        Notes:
        - Will not change gameplay logic.
        - It only adds a label behind all game widgets.
        - If the image fails to load, the game continues using the existing solid bg.
        """
        # Accept either absolute paths or filenames next to the script
        if os.path.isabs(filename):
            path = filename
        else:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

        self.game_bg_path = path

        # Create a label once, and keep it behind everything
        if self.game_bg_label is None:
            self.game_bg_label = tk.Label(self.game_frame, borderwidth=0, highlightthickness=0)
            self.game_bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.game_bg_label.lower()

        try:
            if Image is not None and ImageTk is not None:
                img = Image.open(path).convert("RGBA")
                fitted = self._fit_image_cover(img, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
                self.game_bg_img = ImageTk.PhotoImage(fitted)
            else:
                # Fallback: no Pillow. Use unscaled PhotoImage (may not fit perfectly).
                self.game_bg_img = tk.PhotoImage(file=path)

            self.game_bg_label.config(image=self.game_bg_img)
            self.game_bg_label.lower()
        except (tk.TclError, FileNotFoundError, OSError):
            # If it fails, just remove the image and keep the solid bg.
            self.game_bg_img = None
            if self.game_bg_label is not None:
                self.game_bg_label.config(image="")

    # ---------------- Transparent-looking widgets ----------------

    def _make_label_transparentish(self, parent: tk.Widget, **kwargs) -> tk.Label:
        bg = parent.cget("bg")
        return tk.Label(parent, bg=bg, **kwargs)

    def _make_button_flat(self, parent: tk.Widget, **kwargs) -> tk.Button:
        bg = parent.cget("bg")
        return tk.Button(
            parent,
            bg=bg,
            activebackground=bg,
            relief="groove",
            bd=1,
            highlightthickness=0,
            **kwargs
        )

    # ---------------- Menu ----------------

    def _build_menu(self):
        png_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "final patuchie.png")
        self._set_menu_background_5in(png_path)

        self.menu_frame.config(bg=self.cget("bg"))

        title_fg = "#0b2545"
        subtitle_fg = "#1b3b5a"
        btn_fg = "#0b2545"

        self.menu_frame.grid_rowconfigure(0, weight=0)
        self.menu_frame.grid_rowconfigure(1, weight=0)
        self.menu_frame.grid_rowconfigure(2, weight=0)
        self.menu_frame.grid_rowconfigure(3, weight=0)
        self.menu_frame.grid_rowconfigure(4, weight=0)
        self.menu_frame.grid_rowconfigure(5, weight=0)
        self.menu_frame.grid_rowconfigure(6, weight=0)

        self.menu_frame.grid_columnconfigure(0, weight=3)
        self.menu_frame.grid_columnconfigure(1, weight=2)

        title = self._make_label_transparentish(
            self.menu_frame,
            text="TIC TAC TOE",
            font=("Segoe UI", 18, "bold"),
            fg=title_fg,
        )
        title.grid(row=0, column=1, sticky="ew", pady=(10, 4), padx=(0, 20))

        tagline = self._make_label_transparentish(
            self.menu_frame,
            text="Pick a mode and play!",
            font=("Segoe UI", 9, "bold"),
            fg=subtitle_fg,
        )
        tagline.grid(row=1, column=1, sticky="ew", pady=(0, 8), padx=(0, 20))

        btn_pvp = self._make_button_flat(
            self.menu_frame,
            text="Player vs Player",
            font=("Segoe UI", 11, "bold"),
            fg=btn_fg,
            command=self.start_pvp,
        )
        btn_pvp.grid(row=2, column=1, sticky="ew", pady=4, ipady=3, padx=(0, 20))

        cpu_label = self._make_label_transparentish(
            self.menu_frame,
            text="Player vs CPU Difficulty:",
            font=("Segoe UI", 9, "bold"),
            fg=subtitle_fg,
            anchor="w",
        )
        cpu_label.grid(row=3, column=1, sticky="ew", pady=(8, 4), padx=(0, 20))

        self.diff_var = tk.StringVar(value="Easy")

        diff_menu = tk.OptionMenu(self.menu_frame, self.diff_var, "Easy", "Medium", "Difficult")
        diff_menu.config(
            font=("Segoe UI", 9, "bold"),
            bg=self.menu_frame.cget("bg"),
            fg=btn_fg,
            activebackground=self.menu_frame.cget("bg"),
            activeforeground=btn_fg,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        diff_menu["menu"].config(font=("Segoe UI", 11))
        diff_menu.grid(row=4, column=1, sticky="ew", pady=(0, 4), padx=(0, 20))

        btn_cpu = self._make_button_flat(
            self.menu_frame,
            text="Start vs CPU",
            font=("Segoe UI", 11, "bold"),
            fg=btn_fg,
            command=self.start_cpu,
        )
        btn_cpu.grid(row=5, column=1, sticky="ew", pady=(4, 2), ipady=3, padx=(0, 20))

        btn_quit = self._make_button_flat(
            self.menu_frame,
            text="Quit",
            font=("Segoe UI", 11, "bold"),
            fg="#5a1025",
            command=self.destroy,
        )
        btn_quit.grid(row=6, column=1, sticky="ew", pady=(2, 0), ipady=3, padx=(0, 20))

    # ---------------- Game ----------------

    def _build_game(self):
        # OPTIONAL: set your game background here (change the filename to whatever you want).
        # Put the image next to this script, e.g. "game_bg.png"
        # Comment this out if you don't want a background.
        self.set_game_background("ack.png")

        for c in range(3):
            self.game_frame.grid_columnconfigure(c, weight=1, uniform="grid")
        for r in range(1, 4):
            self.game_frame.grid_rowconfigure(r, weight=1, uniform="grid")

        self.turn_label = tk.Label(
            self.game_frame,
            text="Turn: X",
            font=("Segoe UI", 12, "bold"),
            fg="white",
            # Deep navy blue to match overall theme and background
            bg="#0b2545",
            padx=6,
            pady=2,
        )
        self.turn_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        self.buttons: List[tk.Button] = []
        for r in range(3):
            for c in range(3):
                idx = r * 3 + c
                b = tk.Button(
                    self.game_frame,
                    text=" ",
                    font=("Segoe UI", 16, "bold"),
                    command=lambda i=idx: self.on_cell_clicked(i),
                )
                b.grid(row=r + 1, column=c, padx=4, pady=4, sticky="nsew")
                self.buttons.append(b)

        btn_reset = tk.Button(
            self.game_frame,
            text="Reset",
            font=("Segoe UI", 10),
            width=8,
            command=self.reset_game,
        )
        btn_reset.grid(row=5, column=0, pady=(6, 0))

        btn_menu = tk.Button(
            self.game_frame,
            text="Back to Menu",
            font=("Segoe UI", 10),
            width=10,
            command=self.back_to_menu,
        )
        btn_menu.grid(row=5, column=1, columnspan=2, pady=(6, 0))

        self.mode_label = tk.Label(
            self.game_frame,
            text="Mode: -",
            font=("Segoe UI", 10),
            fg="white",
            # Same navy as turn_label for a consistent look
            bg="#0b2545",
            padx=6,
            pady=2,
        )
        self.mode_label.grid(row=6, column=0, columnspan=3, pady=(10, 0))

    # ---------------- Navigation ----------------

    def _show_menu(self):
        self.game_frame.grid_forget()
        self.menu_frame.grid(row=0, column=0, sticky="nsew")
        self.reset_game(silent=True)

    def _show_game(self):
        self.menu_frame.grid_forget()
        self.game_frame.grid(row=0, column=0, sticky="nsew")

    # ---------------- Start modes ----------------

    def start_pvp(self):
        self.config_data = GameConfig(mode="PVP", cpu_difficulty="Easy")
        self.mode_label.config(text="Mode: Player vs Player")
        self.reset_game(silent=True)
        self._show_game()

    def start_cpu(self):
        diff = self.diff_var.get()
        self.config_data = GameConfig(mode="CPU", cpu_difficulty=diff)
        self.mode_label.config(text=f"Mode: Player vs CPU ({diff})")
        self.reset_game(silent=True)
        self._show_game()

    # ---------------- Game actions ----------------

    def reset_game(self, silent: bool = False):
        self.board = [" "] * 9
        self.current_player = "X"
        self.game_over = False
        for b in self.buttons:
            b.config(text=" ", state="normal")
        self._update_turn_label()

    def back_to_menu(self):
        self._show_menu()

    def on_cell_clicked(self, idx: int):
        if self.game_over:
            return
        if self.board[idx] != " ":
            return

        self._place_move(idx, self.current_player)

        if self._check_end_and_handle():
            return

        if self.config_data and self.config_data.mode == "CPU":
            cpu_symbol = "O"
            human_symbol = "X"
            if self.current_player == cpu_symbol:
                self.after(150, lambda: self._cpu_play(cpu_symbol, human_symbol))

    def _cpu_play(self, cpu_symbol: str, human_symbol: str):
        if self.game_over:
            return

        diff = self.config_data.cpu_difficulty if self.config_data else "Easy"
        move = pick_cpu_move(self.board, diff, cpu_symbol, human_symbol)
        self._place_move(move, cpu_symbol)
        self._check_end_and_handle()

    def _place_move(self, idx: int, symbol: str):
        self.board[idx] = symbol
        self.buttons[idx].config(text=symbol, state="disabled")
        self.current_player = "O" if symbol == "X" else "X"
        self._update_turn_label()

    def _update_turn_label(self):
        if self.game_over:
            return
        self.turn_label.config(text=f"Turn: {self.current_player}")

    def _check_end_and_handle(self) -> bool:
        w = winner_of(self.board)
        if w is not None:
            self.game_over = True
            self.turn_label.config(text=f"Winner: {w}")
            self._disable_all()
            messagebox.showinfo("Game Over", f"{w} wins!")
            return True
        if is_draw(self.board):
            self.game_over = True
            self.turn_label.config(text="Draw!")
            self._disable_all()
            messagebox.showinfo("Game Over", "It's a draw!")
            return True
        return False

    def _disable_all(self):
        for b in self.buttons:
            b.config(state="disabled")


if __name__ == "__main__":
    random.seed()
    app = TicTacToeApp()
    app.mainloop()