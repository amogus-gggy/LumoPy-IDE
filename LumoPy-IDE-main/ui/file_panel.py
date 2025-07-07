import os
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ui.theme import THEMES

class FilePanel:
    def __init__(self, parent, ide):
        self.ide = ide
        self.current_theme = getattr(ide, 'current_theme', 'Тёмная')
        self.current_font = getattr(ide, 'current_font', 'Consolas')
        self.current_size = getattr(ide, 'current_size', 12)
        self.file_panel_root = getattr(ide, 'last_directory', os.path.abspath(os.getcwd()))
        self.file_tree_state = {}  # path: expanded True/False
        self.file_tree_items = []  # flat list of (full_path, level, isdir, expanded)
        self.file_panel_update_job = None

        # Основной фрейм панели
        self.frame = ctk.CTkFrame(parent, fg_color=THEMES[self.current_theme]["editor_bg"], width=150)
        self.frame.pack_propagate(False)

        # Верхняя панель с кнопками
        self.toolbar = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.toolbar.pack(fill="x", padx=2, pady=(4, 2))
        self.add_file_btn = ctk.CTkButton(self.toolbar, text="📄", width=24, height=24, command=lambda: self._create_file_or_folder(False), fg_color="transparent")
        self.add_file_btn.pack(side="left", padx=1)
        self.add_folder_btn = ctk.CTkButton(self.toolbar, text="📁", width=24, height=24, command=lambda: self._create_file_or_folder(True), fg_color="transparent")
        self.add_folder_btn.pack(side="left", padx=1)
        self.refresh_btn = ctk.CTkButton(self.toolbar, text="⟳", width=24, height=24, command=self.refresh, fg_color="transparent")
        self.refresh_btn.pack(side="left", padx=1)
        self.choose_root_btn = ctk.CTkButton(self.toolbar, text="📂", width=24, height=24, command=self.choose_file_panel_folder, fg_color="transparent")
        self.choose_root_btn.pack(side="left", padx=1)

        # Скроллируемый список файлов
        self.scrollable = ctk.CTkScrollableFrame(self.frame, fg_color=THEMES[self.current_theme]["editor_bg"], width=150)
        self.scrollable.pack(expand=True, fill="both", padx=1, pady=(0,2))

        self.file_widgets = []  # Для хранения ссылок на кнопки/лейблы файлов
        self.file_panel_visible = True
        self.schedule_file_panel_update()
        self.populate_file_listbox_tree()

    def refresh(self):
        self.populate_file_listbox_tree()

    def populate_file_listbox_tree(self):
        # Очищаем старые виджеты
        for w in self.file_widgets:
            w.destroy()
        self.file_widgets.clear()
        self.file_tree_items.clear()

        def walk(path, level):
            try:
                entries = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            except Exception:
                return
            for p in entries:
                full_path = os.path.join(path, p)
                isdir = os.path.isdir(full_path)
                expanded = self.file_tree_state.get(full_path, False)
                icon = "📁" if isdir else "📄"
                prefix = "    " * level
                display_text = f"{prefix}{icon} {p}"
                btn = ctk.CTkButton(
                    self.scrollable,
                    text=display_text,
                    anchor="w",
                    width=130,
                    height=24,
                    fg_color=(THEMES[self.current_theme]["output_bg"] if expanded else "transparent") if isdir else "transparent",
                    text_color=THEMES[self.current_theme]["editor_fg"],
                    font=(self.current_font, self.current_size-1),
                    command=lambda fp=full_path, d=isdir, e=expanded: self.on_file_click(fp, d, e, level)
                )
                btn.pack(fill="x", padx=1, pady=1)
                btn.bind("<Button-3>", lambda event, fp=full_path, d=isdir: self._on_file_rmb(event, fp, d))
                btn.bind("<Button-2>", lambda event, fp=full_path, d=isdir: self._on_file_rmb(event, fp, d))
                self.file_widgets.append(btn)
                self.file_tree_items.append((full_path, level, isdir, expanded))
                if isdir and expanded:
                    walk(full_path, level+1)
        walk(self.file_panel_root, 0)

    def on_file_click(self, path, isdir, expanded, level):
        if isdir:
            self.file_tree_state[path] = not expanded
            self.populate_file_listbox_tree()
        elif os.path.isfile(path):
            self.ide.on_file_open(path)

    def schedule_file_panel_update(self):
        if self.file_panel_update_job:
            self.frame.after_cancel(self.file_panel_update_job)
        self.file_panel_update_job = self.frame.after(15000, self.schedule_file_panel_update)

    def update_theme(self, theme, font, size):
        self.current_theme = theme
        self.current_font = font
        self.current_size = size
        self.frame.configure(fg_color=THEMES[theme]["editor_bg"])
        self.scrollable.configure(fg_color=THEMES[theme]["editor_bg"])
        self.populate_file_listbox_tree()

    def choose_file_panel_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.file_panel_root = folder
            self.ide.last_directory = folder
            self.ide._save_settings()
            try:
                os.chdir(folder)
            except Exception:
                pass
            self.populate_file_listbox_tree()
            self.schedule_file_panel_update()

    def _on_file_rmb(self, event, path, isdir):
        menu = tk.Menu(self.frame, tearoff=0)
        menu.config(bg=THEMES[self.current_theme]["editor_bg"], fg=THEMES[self.current_theme]["editor_fg"],
                   activebackground=THEMES[self.current_theme]["output_bg"], activeforeground=THEMES[self.current_theme]["output_fg"])
        if isdir:
            menu.add_command(label="Переименовать папку", command=lambda: self._rename_file_or_folder(path))
            menu.add_command(label="Удалить папку", command=lambda: self._delete_file_or_folder(path))
            menu.add_command(label="Создать файл", command=lambda: self._create_file_or_folder(False, parent_dir=path))
            menu.add_command(label="Создать папку", command=lambda: self._create_file_or_folder(True, parent_dir=path))
        else:
            menu.add_command(label="Переименовать файл", command=lambda: self._rename_file_or_folder(path))
            menu.add_command(label="Удалить файл", command=lambda: self._delete_file_or_folder(path))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _create_file_or_folder(self, is_folder, parent_dir=None):
        from tkinter.simpledialog import askstring
        prompt = "Имя папки:" if is_folder else "Имя файла:"
        name = askstring("Новая папка" if is_folder else "Новый файл", prompt)
        if not name:
            return
        base_dir = parent_dir if parent_dir else self.file_panel_root
        path = os.path.join(base_dir, name)
        try:
            if is_folder:
                os.makedirs(path, exist_ok=True)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    pass
            self.populate_file_listbox_tree()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _rename_file_or_folder(self, path):
        from tkinter.simpledialog import askstring
        base = os.path.basename(path)
        new_name = askstring("Переименовать", f"Новое имя для {base}:")
        if not new_name or new_name == base:
            return
        new_path = os.path.join(os.path.dirname(path), new_name)
        try:
            os.rename(path, new_path)
            self.populate_file_listbox_tree()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _delete_file_or_folder(self, path):
        import shutil
        base = os.path.basename(path)
        if not messagebox.askyesno("Удалить", f"Удалить {base}?"):
            return
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.populate_file_listbox_tree()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e)) 