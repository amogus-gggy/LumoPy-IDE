import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, Text, Scrollbar
import os
import threading
from config import ICON_PATH, WINDOW_TITLE, WINDOW_SIZE
from ui.code_editor import CodeEditor
from ui.theme import THEMES, menu_hover_colors, menu_border_colors, menu_text_colors
import sys
import io
from ui.console import TerminalWidget
from tkinter import ttk
from ui.localization import LANGS, tr
import json
from ui.file_panel import FilePanel

class IDE(ctk.CTk):
    FONTS = ["Consolas", "Fira Code", "Courier New"]
    SIZES = [10, 12, 14, 16, 18]
    SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "settings.json")

    def __init__(self):
        super().__init__()
        print(f"Файл настроек: {self.SETTINGS_FILE}")
        self._load_settings()
        
        # Настройки для отображения в панели задач
        self.title(WINDOW_TITLE)
        self.wm_title(WINDOW_TITLE)
        
        # Устанавливаем иконку и свойства окна для панели задач
        try:
            # Пытаемся установить иконку если она есть
            if ICON_PATH and os.path.exists(ICON_PATH):
                self.iconbitmap(ICON_PATH)
        except:
            pass
            
        # Устанавливаем свойства окна для правильного отображения в панели задач
        self.attributes('-toolwindow', False)  # Убираем флаг toolwindow
        self.wm_attributes('-topmost', False)  # Убираем topmost
        
        # Значения по умолчанию, если не было settings.json
        if not hasattr(self, 'current_theme'):
            self.current_theme = "Тёмная"
        if not hasattr(self, 'current_font'):
            self.current_font = "Consolas"
        if not hasattr(self, 'current_size'):
            self.current_size = 12
        if not hasattr(self, 'current_lang'):
            self.current_lang = 'ru'
        if not hasattr(self, 'terminal_enabled'):
            self.terminal_enabled = True
        if not hasattr(self, 'last_directory'):
            self.last_directory = ""
        if not hasattr(self, 'run_config'):
            self.run_config = {
                "command": "python",
                "args": "",
                "working_dir": ""
            }
        # Верхняя панель с кнопками-меню
        self.menu_frame = ctk.CTkFrame(self, height=36, fg_color=THEMES[self.current_theme]["editor_bg"])
        self.menu_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0, columnspan=3)
        self.menu_frame.grid_columnconfigure(0, weight=0)
        self.menu_frame.grid_columnconfigure(1, weight=0)
        self.menu_frame.grid_columnconfigure(2, weight=0)
        self.menu_frame.grid_columnconfigure(3, weight=1)

        self.file_menu_btn = ctk.CTkButton(
            self.menu_frame, text=tr(self.current_lang, 'File'), width=80, height=32, command=self.show_file_menu,
            fg_color="transparent", hover_color=menu_hover_colors[self.current_theme],
            border_width=1, border_color=menu_border_colors[self.current_theme],
            text_color=menu_text_colors[self.current_theme]
        )
        self.file_menu_btn.grid(row=0, column=0, padx=(8, 0), pady=2)
        self.settings_menu_btn = ctk.CTkButton(
            self.menu_frame, text=tr(self.current_lang, 'Settings'), width=100, height=32, command=self.open_settings,
            fg_color="transparent", hover_color=menu_hover_colors[self.current_theme],
            border_width=1, border_color=menu_border_colors[self.current_theme],
            text_color=menu_text_colors[self.current_theme]
        )
        self.settings_menu_btn.grid(row=0, column=1, padx=(8, 0), pady=2)

        self.file_menu_popup = None

        # --- Основная рабочая область (редактор + консоль) ---
        self.paned_window = ttk.PanedWindow(self, orient="horizontal")
        self.paned_window.grid(row=1, column=0, columnspan=3, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        # --- Файловая панель ---
        self.file_panel = FilePanel(self.paned_window, self)
        self.file_panel_frame = self.file_panel.frame
        self.paned_window.add(self.file_panel_frame, weight=0)
        self.file_panel_visible = True
        # --- Основная рабочая область ---
        self.main_frame = tk.Frame(self.paned_window)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        # --- Вкладки ---
        self.tabs = []  # [{'path': ..., 'name': ..., 'content': ..., 'dirty': ...}]
        self.active_tab = None
        self.tab_frame = tk.Frame(self.main_frame, bg=THEMES[self.current_theme]["editor_bg"], height=28)
        self.tab_frame.pack(side="top", fill="x")
        self.tab_buttons = {}
        self._render_tabs()
        self.inner_paned = ttk.PanedWindow(self.main_frame, orient="vertical")
        self.inner_paned.pack(expand=True, fill="both")
        self.editor = CodeEditor(self.inner_paned)
        self.inner_paned.add(self.editor, weight=3)
        self.editor.scrollbar.master = self.editor
        self.editor.bind('<Key>', self._on_editor_key)
        
        # Устанавливаем расширение файла по умолчанию для подсветки синтаксиса
        self.editor.set_file_extension('.py')
        
        # Привязываем горячие клавиши для автодополнения
        self.editor.bind('<Control-space>', self.editor._trigger_autocomplete)
        self.editor.bind('<Escape>', self.editor._hide_autocomplete)
        
        # Привязываем автопарные скобки
        self.editor.bind('(', lambda e: self.editor._auto_pair('(', ')'))
        self.editor.bind('[', lambda e: self.editor._auto_pair('[', ']'))
        self.editor.bind('{', lambda e: self.editor._auto_pair('{', '}'))
        self.editor.bind('"', lambda e: self.editor._auto_pair('"', '"'))
        self.editor.bind("'", lambda e: self.editor._auto_pair("'", "'"))
        
        # Привязываем горячие клавиши для работы с файлами
        self.bind('<Control-o>', lambda e: self.open_file())
        self.bind('<Control-s>', lambda e: self.save_file())
        self.bind('<Control-n>', lambda e: self._create_new_tab())
        
        # Привязываем горячие клавиши для запуска проекта
        self.bind('<F5>', lambda e: self.run_project())
        self.bind('<Control-r>', lambda e: self.run_project())
        
        # Привязываем горячие клавиши для редактирования
        self.bind('<Control-f>', lambda e: self._show_find_dialog())
        self.bind('<Control-z>', lambda e: self.editor.event_generate('<<Undo>>'))
        self.bind('<Control-y>', lambda e: self.editor.event_generate('<<Redo>>'))
        
        # Привязываем горячие клавиши для копирования/вставки
        self.bind('<Control-c>', lambda e: self.editor.event_generate('<<Copy>>'))
        self.bind('<Control-v>', lambda e: self.editor.event_generate('<<Paste>>'))
        self.bind('<Control-x>', lambda e: self.editor.event_generate('<<Cut>>'))
        
        # Создаем терминал только если он включен в настройках
        self.terminal = None
        if self.terminal_enabled:
            self.terminal = TerminalWidget(self.inner_paned, bg=THEMES[self.current_theme]["output_bg"], fg=THEMES[self.current_theme]["output_fg"], font=(self.current_font, self.current_size))
            self.inner_paned.add(self.terminal, weight=1)
            try:
                self.terminal.write('powershell -NoLogo -NoExit -Command "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new()"\r')
            except Exception:
                pass
        self.paned_window.add(self.main_frame, weight=1)
        # Загружаем конфигурацию проекта
        self._load_project_config()
        # Только теперь применяем тему
        self.apply_theme()

    def update_file_panel_theme(self):
        self.recreate_file_listbox_with_theme()

    def update_sash_color(self):
        theme = THEMES[self.current_theme]
        sash_color = theme.get("sash_bg", theme.get("editor_bg", "#222222"))
        style = ttk.Style()
        style.theme_use('default')
        style.configure("CustomSash.TPanedwindow", sashrelief="flat", sashwidth=8, background=sash_color)
        self.paned_window.configure(style="CustomSash.TPanedwindow")
        self.inner_paned.configure(style="CustomSash.TPanedwindow")

    def apply_theme(self):
        theme = THEMES[self.current_theme]
        self.editor.config(bg=theme["editor_bg"], fg=theme["editor_fg"], insertbackground=theme["editor_fg"], font=(self.current_font, self.current_size))
        if hasattr(self, 'terminal') and self.terminal:
            self.terminal.set_theme(theme["output_bg"], theme["output_fg"])
        self.editor.force_highlight()
        for btn in [self.file_menu_btn, self.settings_menu_btn]:
            btn.configure(
                hover_color=menu_hover_colors[self.current_theme],
                border_color=menu_border_colors[self.current_theme],
                text_color=menu_text_colors[self.current_theme]
            )
        self.menu_frame.configure(fg_color=theme["editor_bg"])
        self.menu_frame.update_idletasks()
        self.file_panel.update_theme(self.current_theme, self.current_font, self.current_size)
        self.update_sash_color()
        self._render_tabs()
        self._save_settings()

    def _update_terminal_visibility(self):
        """Обновляет видимость терминала в зависимости от настроек"""
        if self.terminal_enabled:
            if not self.terminal:
                # Создаем терминал если его нет
                self.terminal = TerminalWidget(self.inner_paned, bg=THEMES[self.current_theme]["output_bg"], fg=THEMES[self.current_theme]["output_fg"], font=(self.current_font, self.current_size))
                self.inner_paned.add(self.terminal, weight=1)
                try:
                    self.terminal.write('powershell -NoLogo -NoExit -Command "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new()"\r')
                except Exception:
                    pass
        else:
            if self.terminal:
                # Удаляем терминал если он есть
                self.inner_paned.remove(self.terminal)
                self.terminal.destroy()
                self.terminal = None

    def open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title(tr(self.current_lang, 'SettingsTitle'))
        win.geometry("500x450")
        win.grab_set()
        win.transient(self)
        win.focus_set()

        # Выбор языка
        ctk.CTkLabel(win, text="Language:").pack(anchor="w", padx=10, pady=(10,0))
        lang_var = ctk.StringVar(value=self.current_lang)
        lang_menu = ctk.CTkOptionMenu(win, variable=lang_var, values=list(LANGS.keys()), command=lambda _: preview())
        lang_menu.pack(anchor="w", padx=20)

        ctk.CTkLabel(win, text=tr(self.current_lang, 'Theme')).pack(anchor="w", padx=10, pady=(10,0))
        theme_var = ctk.StringVar(value=self.current_theme)
        for theme in THEMES:
            ctk.CTkRadioButton(win, text=theme, variable=theme_var, value=theme, command=lambda: preview()).pack(anchor="w", padx=20)

        ctk.CTkLabel(win, text=tr(self.current_lang, 'Font')).pack(anchor="w", padx=10, pady=(10,0))
        font_var = ctk.StringVar(value=self.current_font)
        font_menu = ctk.CTkOptionMenu(win, variable=font_var, values=self.FONTS, command=lambda _: preview())
        font_menu.pack(anchor="w", padx=20)

        ctk.CTkLabel(win, text=tr(self.current_lang, 'Size')).pack(anchor="w", padx=10, pady=(10,0))
        size_var = ctk.StringVar(value=str(self.current_size))
        size_menu = ctk.CTkOptionMenu(win, variable=size_var, values=[str(s) for s in self.SIZES], command=lambda _: preview())
        size_menu.pack(anchor="w", padx=20)

        # Настройка терминала
        terminal_var = ctk.BooleanVar(value=self.terminal_enabled)
        terminal_checkbox = ctk.CTkCheckBox(win, text=tr(self.current_lang, 'Terminal'), variable=terminal_var, command=lambda: preview())
        terminal_checkbox.pack(anchor="w", padx=10, pady=(10,0))

        def preview():
            self.current_lang = lang_var.get()
            self.current_theme = theme_var.get()
            self.current_font = font_var.get()
            self.current_size = int(size_var.get())
            self.terminal_enabled = terminal_var.get()
            self.apply_theme()
            self._update_terminal_visibility()
            self._save_settings()

    def show_file_menu(self):
        if self.file_menu_popup and self.file_menu_popup.winfo_exists():
            self.file_menu_popup.destroy()
            return
        self.file_menu_popup = ctk.CTkToplevel(self)
        self.file_menu_popup.overrideredirect(True)
        self.file_menu_popup.lift()
        self.file_menu_popup.geometry(f"160x180+{self.file_menu_btn.winfo_rootx()}+{self.file_menu_btn.winfo_rooty() + self.file_menu_btn.winfo_height()}")
        self.file_menu_popup.configure(bg=THEMES[self.current_theme]["editor_bg"])
        hover_color = menu_hover_colors[self.current_theme]
        border_color = menu_border_colors[self.current_theme]
        text_color = menu_text_colors[self.current_theme]
        open_btn = ctk.CTkButton(self.file_menu_popup, text=tr(self.current_lang, 'Open'), width=140, height=32, command=lambda: self._file_menu_action('open'), fg_color="transparent", hover_color=hover_color, border_width=1, border_color=border_color, text_color=text_color)
        open_btn.pack(padx=5, pady=(5, 2))
        save_btn = ctk.CTkButton(self.file_menu_popup, text=tr(self.current_lang, 'Save'), width=140, height=32, command=lambda: self._file_menu_action('save'), fg_color="transparent", hover_color=hover_color, border_width=1, border_color=border_color, text_color=text_color)
        save_btn.pack(padx=5, pady=(0, 2))
        folder_btn = ctk.CTkButton(self.file_menu_popup, text=tr(self.current_lang, 'Folder'), width=140, height=32, command=self.file_panel.choose_file_panel_folder, fg_color="transparent", hover_color=hover_color, border_width=1, border_color=border_color, text_color=text_color)
        folder_btn.pack(padx=5, pady=(0, 2))
        run_btn = ctk.CTkButton(self.file_menu_popup, text="Запустить проект", width=140, height=32, command=self.run_project, fg_color="transparent", hover_color=hover_color, border_width=1, border_color=border_color, text_color=text_color)
        run_btn.pack(padx=5, pady=(0, 2))
        config_btn = ctk.CTkButton(self.file_menu_popup, text="Настройки запуска", width=140, height=32, command=self.open_run_config, fg_color="transparent", hover_color=hover_color, border_width=1, border_color=border_color, text_color=text_color)
        config_btn.pack(padx=5, pady=(0, 5))
        self.file_menu_popup.bind("<FocusOut>", lambda e: self.file_menu_popup.destroy())
        self.file_menu_popup.focus_set()

    def _file_menu_action(self, action):
        if self.file_menu_popup and self.file_menu_popup.winfo_exists():
            self.file_menu_popup.destroy()
        if action == 'open':
            self.open_file()
        elif action == 'save':
            self.save_file()

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if file_path:
            # Проверяем, открыт ли уже файл
            for tab in self.tabs:
                if tab["path"] == file_path:
                    self._switch_tab(tab)
                    return
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tab = {"path": file_path, "name": os.path.basename(file_path), "content": content, "dirty": False}
            self.tabs.append(tab)
            self._switch_tab(tab)

    def save_file(self):
        if not self.active_tab:
            return
        file_path = self.active_tab["path"]
        if not file_path:
            file_path = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python files", "*.py"), ("All files", "*.*")])
            if not file_path:
                return
            self.active_tab["path"] = file_path
            self.active_tab["name"] = os.path.basename(file_path)
            self._render_tabs()
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.editor.get("1.0", tk.END))
        self.active_tab["dirty"] = False
        self._render_tabs()

    def destroy(self):
        if hasattr(self, 'file_panel') and hasattr(self.file_panel, 'destroy'):
            self.file_panel.destroy()
        super().destroy()

    def set_treeview_black(self):
        self.file_listbox.tk.call("ttk::style", "configure", "Treeview",
            "-background", "#111111",
            "-fieldbackground", "#111111",
            "-foreground", "#ffffff",
            "-font", f"{self.current_font} {self.current_size-1}"
        )
        self.file_listbox.tk.call("ttk::style", "map", "Treeview",
            "-background", ["selected", "#222222"]
        )

    def set_treeview_colors(self, bg, fg, select_bg=None, select_fg=None):
        # Меняем цвета через низкоуровневый tk.call
        self.file_listbox.tk.call("ttk::style", "configure", "Treeview",
            "-background", bg,
            "-fieldbackground", bg,
            "-foreground", fg
        )
        if select_bg:
            self.file_listbox.tk.call("ttk::style", "map", "Treeview",
                "-background", ["selected", select_bg]
            )
        if select_fg:
            self.file_listbox.tk.call("ttk::style", "map", "Treeview",
                "-foreground", ["selected", select_fg]
            )

    def recreate_file_tree(self, bg, fg):
        # Удаляем старый Treeview
        if hasattr(self, 'file_listbox') and self.file_listbox.winfo_exists():
            self.file_listbox.pack_forget()
            self.file_listbox.destroy()
        self.file_listbox = tk.Listbox(
            self.file_panel_frame,
            bg=bg,
            fg=fg,
            selectbackground=bg,
            selectforeground=fg,
            font=(self.current_font, self.current_size-1),
            activestyle='none',
            borderwidth=0,
            highlightthickness=0
        )
        self.file_listbox.pack(expand=True, fill="both", padx=2, pady=2)
        self.file_listbox.bind("<Double-1>", self.on_file_open_listbox)
        self.file_panel_visible = True
        self.file_tree_state = {}  # path: expanded True/False
        self.file_tree_items = []  # flat list of (path, level, isdir, expanded)
        self.file_panel_update_job = None
        self.schedule_file_panel_update()
        self.populate_file_listbox_tree()
        self.file_listbox.update_idletasks()
        self.set_treeview_colors(bg, fg, select_bg="#222222", select_fg="#ffffff")
        self.file_listbox.update_idletasks()
        # Создаём новый Treeview с нужными цветами через параметры конструктора
        self.file_listbox = tk.Listbox(self.file_panel_frame, columns=("fullpath",), show="tree", 
                                      style="Treeview", 
                                      selectmode="browse")
        try:
            self.file_listbox.configure(background=bg, foreground=fg, fieldbackground=bg)
        except Exception:
            print("Не поддерживается") # если не поддерживается, игнорируем
        self.file_listbox.pack(expand=True, fill="both", padx=2, pady=2)
        self.file_listbox.bind("<Double-1>", self.on_file_open_listbox)
        self.file_listbox.column("#0", width=180, stretch=False)
        self.populate_file_listbox_tree() 

    def _on_editor_key(self, event=None):
        # Не помечаем вкладку как грязную при навигации стрелками
        if event and event.keysym in ['Up', 'Down', 'Left', 'Right', 'Home', 'End', 'Page_Up', 'Page_Down']:
            return
            
        # Если нет активной вкладки, создаем новую "Безымянный"
        if not self.active_tab:
            untitled_tab = {"path": None, "name": tr(self.current_lang, 'Untitled'), "content": "", "dirty": False}
            self.tabs.append(untitled_tab)
            self.active_tab = untitled_tab
            # Устанавливаем расширение файла для подсветки синтаксиса
            self.editor.set_file_extension('.py')
            self._render_tabs()
        else:
            # Помечаем как грязную только если содержимое действительно изменилось
            if self.editor.edit_modified():
                self.active_tab["dirty"] = True
                self._render_tabs()

    def _on_file_listbox_rmb(self, event):
        # Проверяем, что клик был по file_listbox
        if event.widget != self.file_listbox:
            return
        idx = self.file_listbox.nearest(event.y)
        bbox = self.file_listbox.bbox(idx)
        if bbox and event.y >= bbox[1] and event.y <= bbox[1] + bbox[3]:
            # ПКМ по файлу/папке
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(idx)
            path, level, isdir, expanded = self.file_tree_items[idx]
            self._show_file_context_menu_menu(event, path, isdir)
        else:
            self.file_listbox.selection_clear(0, tk.END)
            self._show_empty_context_menu_menu(event)

    def _show_file_context_menu_menu(self, event, path, isdir):
        menu = tk.Menu(self, tearoff=0)
        menu.config(bg=THEMES[self.current_theme]["editor_bg"], fg=THEMES[self.current_theme]["editor_fg"],
                   activebackground=THEMES[self.current_theme]["output_bg"], activeforeground=THEMES[self.current_theme]["output_fg"])
        menu.add_command(label=tr(self.current_lang, 'Rename'), command=lambda: self._rename_file_or_folder(path))
        menu.add_command(label=tr(self.current_lang, 'Delete'), command=lambda: self._delete_file_or_folder(path))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _show_empty_context_menu_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.config(bg=THEMES[self.current_theme]["editor_bg"], fg=THEMES[self.current_theme]["editor_fg"],
                   activebackground=THEMES[self.current_theme]["output_bg"], activeforeground=THEMES[self.current_theme]["output_fg"])
        menu.add_command(label=tr(self.current_lang, 'NewFile'), command=lambda: self._create_file_or_folder(is_folder=False))
        menu.add_command(label=tr(self.current_lang, 'NewFolder'), command=lambda: self._create_file_or_folder(is_folder=True))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _create_file_or_folder(self, is_folder):
        from tkinter.simpledialog import askstring
        prompt = tr(self.current_lang, 'CreatePromptFolder') if is_folder else tr(self.current_lang, 'CreatePromptFile')
        name = askstring(tr(self.current_lang, 'NewFolder') if is_folder else tr(self.current_lang, 'NewFile'), prompt)
        if not name:
            return
        path = os.path.join(self.file_panel.file_panel_root, name)
        try:
            if is_folder:
                os.makedirs(path, exist_ok=True)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    pass
            self.populate_file_listbox_tree()
        except Exception as e:
            messagebox.showerror(tr(self.current_lang, 'Error'), str(e))

    def _rename_file_or_folder(self, path):
        from tkinter.simpledialog import askstring
        base = os.path.basename(path)
        new_name = askstring(tr(self.current_lang, 'Rename'), tr(self.current_lang, 'RenamePrompt', name=base))
        if not new_name or new_name == base:
            return
        new_path = os.path.join(os.path.dirname(path), new_name)
        try:
            os.rename(path, new_path)
            self.populate_file_listbox_tree()
        except Exception as e:
            messagebox.showerror(tr(self.current_lang, 'Error'), str(e))

    def _delete_file_or_folder(self, path):
        import shutil
        base = os.path.basename(path)
        if not messagebox.askyesno(tr(self.current_lang, 'Delete'), tr(self.current_lang, 'DeleteConfirm', name=base)):
            return
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.populate_file_listbox_tree()
        except Exception as e:
            messagebox.showerror(tr(self.current_lang, 'Error'), str(e))

    def _save_settings(self):
        data = {
            "theme": self.current_theme,
            "font": self.current_font,
            "size": self.current_size,
            "lang": self.current_lang,
            "terminal_enabled": self.terminal_enabled,
            "last_directory": self.last_directory
        }
        try:
            # Убеждаемся, что директория существует
            os.makedirs(os.path.dirname(self.SETTINGS_FILE), exist_ok=True)
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Не удалось сохранить настройки: {e}")

    def _load_settings(self):
        try:
            with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.current_theme = data.get("theme", "Тёмная")
            self.current_font = data.get("font", "Consolas")
            self.current_size = data.get("size", 12)
            self.current_lang = data.get("lang", "ru")
            self.terminal_enabled = data.get("terminal_enabled", True)
            self.last_directory = data.get("last_directory", "")
            # Конфигурация запуска загружается отдельно из проекта
            self.run_config = {
                "command": "python",
                "args": "",
                "working_dir": ""
            }
        except Exception:
            pass 

    def _render_tabs(self):
        # Очищаем старые кнопки
        for btn in getattr(self, 'tab_buttons', {}).values():
            btn["frame"].destroy() if "frame" in btn else btn["btn"].destroy()
        self.tab_buttons = {}
        self.tab_frame.config(bg=THEMES[self.current_theme]["editor_bg"])
        if not self.tabs:
            # Если вкладок нет, показываем кнопку +
            add_btn = tk.Button(self.tab_frame, text="+", bd=0, bg=THEMES[self.current_theme]["editor_bg"], fg="#aaa", font=("Arial", 12, "bold"), command=self.open_file)
            add_btn.pack(side="left", padx=(4,0))
            self.tab_buttons["__add__"] = {"btn": add_btn}
            return
        for i, tab in enumerate(self.tabs):
            active_bg = THEMES[self.current_theme].get("output_bg", "#222") if tab is self.active_tab else THEMES[self.current_theme]["editor_bg"]
            f = tk.Frame(self.tab_frame, bg=active_bg, bd=0, relief="flat")
            f.pack(side="left", padx=(0,2), pady=2)
            btn = tk.Button(f, text=tab["name"], bd=0, bg=active_bg, fg=THEMES[self.current_theme]["editor_fg"] if tab is self.active_tab else "#aaa", font=("Consolas", 10, "bold"), command=lambda t=tab: self._switch_tab(t), activebackground=THEMES[self.current_theme]["output_bg"])
            btn.pack(side="left")
            close_btn = tk.Button(f, text="✕", bd=0, bg=active_bg, fg="#e06c75", font=("Arial", 9), command=lambda t=tab: self._close_tab(t), activebackground=THEMES[self.current_theme]["output_bg"])
            close_btn.pack(side="left")
            self.tab_buttons[tab["path"]] = {"frame": f, "btn": btn, "close": close_btn}
        # Кнопка для новой вкладки
        add_btn = tk.Button(self.tab_frame, text="+", bd=0, bg=THEMES[self.current_theme]["editor_bg"], fg="#aaa", font=("Arial", 12, "bold"), command=self.open_file)
        add_btn.pack(side="left", padx=(4,0))
        self.tab_buttons["__add__"] = {"btn": add_btn}

    def _switch_tab(self, tab):
        if self.active_tab:
            # Сохраняем содержимое предыдущей вкладки
            self.active_tab["content"] = self.editor.get("1.0", tk.END)
        self.active_tab = tab
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", tab["content"])
        
        # Устанавливаем правильное расширение файла для подсветки синтаксиса
        if tab["path"]:
            file_extension = os.path.splitext(tab["path"])[1]
            self.editor.set_file_extension(file_extension)
        else:
            # Для безымянных файлов используем Python по умолчанию
            self.editor.set_file_extension('.py')
            
        self.editor.force_highlight()
        self._render_tabs()

    def _close_tab(self, tab):
        idx = self.tabs.index(tab)
        self.tabs.remove(tab)
        if self.active_tab is tab:
            # Переключаемся на соседнюю вкладку
            if self.tabs:
                self.active_tab = self.tabs[max(0, idx-1)]
                self.editor.delete("1.0", tk.END)
                self.editor.insert("1.0", self.active_tab["content"])
                
                # Устанавливаем правильное расширение файла для подсветки синтаксиса
                if self.active_tab["path"]:
                    file_extension = os.path.splitext(self.active_tab["path"])[1]
                    self.editor.set_file_extension(file_extension)
                else:
                    # Для безымянных файлов используем Python по умолчанию
                    self.editor.set_file_extension('.py')
                    
                self.editor.force_highlight()
            else:
                self.active_tab = None
                self.editor.delete("1.0", tk.END)
        self._render_tabs()

    def _show_find_dialog(self, event=None):
        """Показывает диалог поиска (заглушка)"""
        # Простая реализация поиска
        from tkinter import simpledialog
        search_text = simpledialog.askstring("Поиск", "Введите текст для поиска:")
        if search_text:
            # Простой поиск в текущем содержимом
            content = self.editor.get("1.0", tk.END)
            if search_text in content:
                # Находим позицию и выделяем
                start_pos = content.find(search_text)
                end_pos = start_pos + len(search_text)
                self.editor.tag_remove("search", "1.0", tk.END)
                self.editor.tag_add("search", f"1.0+{start_pos}c", f"1.0+{end_pos}c")
                self.editor.tag_config("search", background="yellow", foreground="black")
                self.editor.see(f"1.0+{start_pos}c")
            else:
                from tkinter import messagebox
                messagebox.showinfo("Поиск", "Текст не найден") 

    def _create_new_tab(self):
        """Создает новую пустую вкладку"""
        tab = {"path": None, "name": tr(self.current_lang, 'Untitled'), "content": "", "dirty": False}
        self.tabs.append(tab)
        self._switch_tab(tab)

    def _load_project_config(self):
        """Загружает конфигурацию запуска проекта из .lumocfg/run.json"""
        config_path = os.path.join(self.file_panel.file_panel_root, ".lumocfg", "run.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self.run_config = json.load(f)
            else:
                # Создаем конфигурацию по умолчанию
                self._create_default_project_config()
        except Exception as e:
            print(f"Ошибка загрузки конфигурации проекта: {e}")
            self._create_default_project_config()

    def _create_default_project_config(self):
        """Создает конфигурацию запуска по умолчанию для проекта"""
        config_dir = os.path.join(self.file_panel.file_panel_root, ".lumocfg")
        config_path = os.path.join(config_dir, "run.json")
        
        # Определяем тип проекта по содержимому папки
        project_type = self._detect_project_type()
        
        default_config = {
            "command": project_type["command"],
            "args": project_type["args"],
            "working_dir": "",
            "description": project_type["description"]
        }
        
        try:
            os.makedirs(config_dir, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            self.run_config = default_config
        except Exception as e:
            print(f"Ошибка создания конфигурации проекта: {e}")

    def _detect_project_type(self):
        """Определяет тип проекта по содержимому папки"""
        root = self.file_panel.file_panel_root
        if not root or not os.path.exists(root):
            return {
                "command": "python",
                "args": "main.py",
                "description": "Python проект (путь не найден)"
            }
        files = os.listdir(root)
        # Python проект
        if any(f.endswith('.py') for f in files) or 'requirements.txt' in files:
            return {
                "command": "python",
                "args": "main.py",
                "description": "Python проект"
            }
        # По умолчанию Python
        return {
            "command": "python",
            "args": "main.py",
            "description": "Python проект"
        }

    def _save_project_config(self):
        """Сохраняет конфигурацию запуска проекта"""
        config_path = os.path.join(self.file_panel.file_panel_root, ".lumocfg", "run.json")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.run_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации проекта: {e}")

    def run_project(self):
        """Запускает проект в новом окне терминала с UTF-8 кодировкой"""
        if not self.run_config:
            messagebox.showwarning("Предупреждение", "Конфигурация запуска не найдена")
            return
        
        command = self.run_config.get("command", "python")
        args = self.run_config.get("args", "")
        working_dir = self.run_config.get("working_dir", "")
        
        if working_dir:
            full_working_dir = os.path.join(self.file_panel.file_panel_root, working_dir)
        else:
            full_working_dir = self.file_panel.file_panel_root
        
        try:
            # Формируем полную команду
            if args:
                full_command = f"{command} {args}"
            else:
                full_command = command
            
            # Открываем новое окно терминала с UTF-8 кодировкой
            import subprocess
            import sys
            
            print(f"Запуск проекта в новом окне терминала...")
            print(f"Команда: {full_command}")
            print(f"Рабочая директория: {full_working_dir}")
            
            # Команда для открытия нового окна терминала
            if sys.platform == "win32":
                # Windows - используем более простой подход
                try:
                    # Создаем bat файл для запуска
                    import tempfile
                    
                    # Создаем временный bat файл
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False, encoding='utf-8') as f:
                        bat_content = f"""@echo off
chcp 65001 > nul
cd /d "{full_working_dir}"
echo Запуск проекта...
echo Команда: {full_command}
echo.
{full_command}
echo.
echo Проект завершен. Нажмите любую клавишу для выхода...
pause > nul
"""
                        f.write(bat_content)
                        bat_file = f.name
                    
                    # Запускаем bat файл в новом окне
                    subprocess.run(['start', 'cmd', '/k', bat_file], shell=True)
                    
                    # Удаляем bat файл через некоторое время
                    def cleanup_bat():
                        import time
                        time.sleep(2)
                        try:
                            os.unlink(bat_file)
                        except:
                            pass
                    
                    threading.Thread(target=cleanup_bat, daemon=True).start()
                    
                except Exception as e:
                    print(f"Ошибка создания bat файла: {e}")
                    # Fallback: простой запуск
                    subprocess.Popen([command] + args.split() if args else [command], cwd=full_working_dir)
            else:
                # Linux/Mac - используем терминал по умолчанию
                terminal_cmd = [
                    "gnome-terminal", "--", "bash", "-c",
                    f"cd '{full_working_dir}' && echo 'Запуск проекта...' && {full_command}; exec bash"
                ]
                subprocess.Popen(terminal_cmd, cwd=full_working_dir)
            
            print(f"Проект запущен!")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить проект: {e}")
            print(f"Ошибка запуска проекта: {e}")

    def open_run_config(self):
        """Открывает диалог настройки конфигурации запуска"""
        self._show_run_config_dialog()

    def _show_run_config_dialog(self):
        """Показывает диалог настройки конфигурации запуска"""
        win = ctk.CTkToplevel(self)
        win.title("Конфигурация запуска проекта")
        win.geometry("600x500")
        win.grab_set()
        win.transient(self)
        win.focus_set()

        # Загружаем текущую конфигурацию
        self._load_project_config()

        # Команда
        ctk.CTkLabel(win, text="Команда:").pack(anchor="w", padx=10, pady=(10,0))
        command_var = ctk.StringVar(value=self.run_config.get("command", "python"))
        command_entry = ctk.CTkEntry(win, textvariable=command_var, width=400)
        command_entry.pack(anchor="w", padx=20, pady=(5,10))

        # Аргументы
        ctk.CTkLabel(win, text="Аргументы:").pack(anchor="w", padx=10, pady=(10,0))
        args_var = ctk.StringVar(value=self.run_config.get("args", ""))
        args_entry = ctk.CTkEntry(win, textvariable=args_var, width=400)
        args_entry.pack(anchor="w", padx=20, pady=(5,10))

        # Рабочая директория
        ctk.CTkLabel(win, text="Рабочая директория (относительно корня проекта):").pack(anchor="w", padx=10, pady=(10,0))
        working_dir_var = ctk.StringVar(value=self.run_config.get("working_dir", ""))
        working_dir_entry = ctk.CTkEntry(win, textvariable=working_dir_var, width=400)
        working_dir_entry.pack(anchor="w", padx=20, pady=(5,10))

        # Описание
        ctk.CTkLabel(win, text="Описание:").pack(anchor="w", padx=10, pady=(10,0))
        description_var = ctk.StringVar(value=self.run_config.get("description", ""))
        description_entry = ctk.CTkEntry(win, textvariable=description_var, width=400)
        description_entry.pack(anchor="w", padx=20, pady=(5,10))

        # Кнопки быстрых настроек
        ctk.CTkLabel(win, text="Быстрые настройки:").pack(anchor="w", padx=10, pady=(20,0))
        
        buttons_frame = ctk.CTkFrame(win)
        buttons_frame.pack(anchor="w", padx=20, pady=(5,10), fill="x")
        
        def set_python_config():
            command_var.set("python")
            args_var.set("main.py")
            description_var.set("Python проект")
        
        def set_python_module_config():
            command_var.set("python")
            args_var.set("-m module_name")
            description_var.set("Python модуль")
        
        def set_python_script_config():
            command_var.set("python")
            args_var.set("script.py")
            description_var.set("Python скрипт")
        
        ctk.CTkButton(buttons_frame, text="Python (main.py)", command=set_python_config, width=120).pack(side="left", padx=5)
        ctk.CTkButton(buttons_frame, text="Python модуль", command=set_python_module_config, width=120).pack(side="left", padx=5)
        ctk.CTkButton(buttons_frame, text="Python скрипт", command=set_python_script_config, width=120).pack(side="left", padx=5)

        # Кнопки действий
        actions_frame = ctk.CTkFrame(win)
        actions_frame.pack(anchor="w", padx=20, pady=(20,10), fill="x")
        
        def save_config():
            self.run_config = {
                "command": command_var.get(),
                "args": args_var.get(),
                "working_dir": working_dir_var.get(),
                "description": description_var.get()
            }
            self._save_project_config()
            messagebox.showinfo("Успех", "Конфигурация запуска сохранена")
            win.destroy()
        
        ctk.CTkButton(actions_frame, text="Сохранить", command=save_config, width=100).pack(side="left", padx=5)
        ctk.CTkButton(actions_frame, text="Отмена", command=win.destroy, width=100).pack(side="left", padx=5)

    def on_file_open(self, path):
        # Открывает файл из файловой панели во вкладке
        for tab in self.tabs:
            if tab["path"] == path:
                self._switch_tab(tab)
                return
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        tab = {"path": path, "name": os.path.basename(path), "content": content, "dirty": False}
        self.tabs.append(tab)
        self._switch_tab(tab) 
