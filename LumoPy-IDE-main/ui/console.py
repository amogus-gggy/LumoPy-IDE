import tkinter as tk
from tkterm import Terminal
import os

os.environ["LANG"] = "ru_RU.UTF-8"
os.environ["PYTHONIOENCODING"] = "utf-8"

class TerminalWidget(Terminal):
    def __init__(self, master, bg='#222', fg='#fff', font=None, **kwargs):
        if font is None:
            font = ("Consolas", 12)
        super().__init__(master, bg=bg, **kwargs)
        try:
            self.config(fg=fg, font=font)
        except Exception:
            pass
        # self.pack(fill=tk.BOTH, expand=True)  # Удалено для совместимости с grid
        self.focus_set()
        # Автоматически переключаем кодовую страницу на UTF-8
        try:
            self.write('echo 123')
        except Exception:
            pass

    def set_theme(self, bg, fg):
        self.config(bg=bg)
        try:
            self.config(fg=fg)
        except Exception:
            pass 