import tkinter as tk
from tkinter import ttk
import re
import builtins
import keyword

class SimpleAutocomplete:
    def __init__(self, editor):
        self.editor = editor
        self.popup = None
        self.listbox = None
        self.completions = []
        self.current_completion = 0
        
        # Базовые предложения автодополнения
        self.builtin_functions = [name for name in dir(builtins) if not name.startswith('_')]
        self.keywords = keyword.kwlist
        self.basic_completions = [
            'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'tuple', 'set',
            'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
            'open', 'input', 'type', 'isinstance', 'hasattr', 'getattr', 'setattr',
            'dir', 'help', 'id', 'hash', 'abs', 'round', 'min', 'max', 'sum',
            'all', 'any', 'bool', 'chr', 'ord', 'bin', 'hex', 'oct', 'format',
            'join', 'split', 'strip', 'replace', 'find', 'index', 'count',
            'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'copy',
            'keys', 'values', 'items', 'get', 'update', 'setdefault',
            'True', 'False', 'None', 'self', 'def', 'class', 'import', 'from',
            'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally',
            'with', 'as', 'return', 'yield', 'break', 'continue', 'pass',
            'raise', 'assert', 'del', 'global', 'nonlocal', 'lambda'
        ]
        
        # Привязываем события
        self.editor.bind('<KeyRelease>', self.on_key_release)
        self.editor.bind('<Control-space>', self.show_completions)
        self.editor.bind('<Escape>', self.hide_popup)
        
    def get_current_word(self):
        """Получает текущее слово под курсором"""
        cursor_pos = self.editor.index(tk.INSERT)
        line, col = map(int, cursor_pos.split('.'))
        
        # Получаем текст текущей строки
        line_text = self.editor.get(f"{line}.0", f"{line}.end")
        
        # Ищем начало слова
        word_start = col
        while word_start > 0 and (line_text[word_start - 1].isalnum() or line_text[word_start - 1] in '_.'):
            word_start -= 1
            
        # Ищем конец слова
        word_end = col
        while word_end < len(line_text) and (line_text[word_end].isalnum() or line_text[word_end] in '_.'):
            word_end += 1
            
        current_word = line_text[word_start:word_end]
        return current_word, word_start, word_end
        
    def get_completions(self, word):
        """Получает предложения автодополнения для слова"""
        if not word:
            return []
            
        word_lower = word.lower()
        completions = []
        
        # Добавляем встроенные функции
        for func in self.builtin_functions:
            if func.lower().startswith(word_lower):
                completions.append(func)
                
        # Добавляем ключевые слова
        for kw in self.keywords:
            if kw.lower().startswith(word_lower):
                completions.append(kw)
                
        # Добавляем базовые предложения
        for comp in self.basic_completions:
            if comp.lower().startswith(word_lower):
                completions.append(comp)
                
        # Получаем переменные из текущего кода
        code = self.editor.get("1.0", tk.END)
        variables = self.extract_variables(code)
        for var in variables:
            if var.lower().startswith(word_lower):
                completions.append(var)
                
        # Убираем дубликаты и сортируем
        completions = sorted(list(set(completions)))
        return completions[:20]  # Ограничиваем количество
        
    def extract_variables(self, code):
        """Извлекает переменные из кода"""
        variables = []
        
        # Ищем присваивания переменных
        assignment_pattern = r'(\w+)\s*='
        matches = re.findall(assignment_pattern, code)
        variables.extend(matches)
        
        # Ищем параметры функций
        def_pattern = r'def\s+\w+\s*\(([^)]*)\)'
        matches = re.findall(def_pattern, code)
        for match in matches:
            params = [p.strip() for p in match.split(',')]
            for param in params:
                if param and not param.startswith('*'):
                    variables.append(param)
                    
        # Ищем параметры классов
        class_pattern = r'class\s+\w+\s*\(([^)]*)\)'
        matches = re.findall(class_pattern, code)
        for match in matches:
            params = [p.strip() for p in match.split(',')]
            for param in params:
                if param and not param.startswith('*'):
                    variables.append(param)
                    
        return list(set(variables))
        
    def create_popup(self):
        """Создает всплывающее окно автодополнения"""
        if self.popup:
            self.popup.destroy()
            
        self.popup = tk.Toplevel(self.editor)
        self.popup.overrideredirect(True)
        self.popup.configure(bg='#2d2d2d')
        
        # Создаем рамку
        frame = tk.Frame(self.popup, bg='#2d2d2d', relief='solid', bd=1)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Создаем список
        self.listbox = tk.Listbox(
            frame,
            bg='#2d2d2d',
            fg='#ffffff',
            selectbackground='#404040',
            selectforeground='#ffffff',
            font=('Consolas', 10),
            borderwidth=0,
            highlightthickness=0,
            activestyle='none',
            height=8
        )
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Привязываем события
        self.listbox.bind('<Key>', self.on_popup_key)
        self.listbox.bind('<Button-1>', self.on_select)
        self.listbox.bind('<Return>', self.on_select)
        self.listbox.bind('<Escape>', self.hide_popup)
        
    def show_completions(self, event=None):
        """Показывает автодополнение"""
        current_word, word_start, word_end = self.get_current_word()
        
        if len(current_word) < 1:
            self.hide_popup()
            return
            
        # Получаем предложения
        self.completions = self.get_completions(current_word)
        
        if not self.completions:
            self.hide_popup()
            return
            
        # Создаем окно если нужно
        if not self.popup:
            self.create_popup()
            
        # Очищаем список
        self.listbox.delete(0, tk.END)
        
        # Добавляем предложения
        for completion in self.completions:
            self.listbox.insert(tk.END, completion)
            
        # Позиционируем окно
        cursor_pos = self.editor.index(tk.INSERT)
        bbox = self.editor.bbox(cursor_pos)
        if bbox:
            x, y, w, h = bbox
            window_x = self.editor.winfo_rootx() + x
            window_y = self.editor.winfo_rooty() + y + h
            
            # Устанавливаем размер окна
            self.popup.geometry(f"200x{min(len(self.completions) * 20 + 10, 160)}+{window_x}+{window_y}")
            self.popup.deiconify()
            
            # Выбираем первый элемент
            if self.listbox.size() > 0:
                self.listbox.selection_set(0)
                self.current_completion = 0
                
            # Фокусируемся на списке
            self.listbox.focus_set()
            
    def hide_popup(self, event=None):
        """Скрывает всплывающее окно"""
        if self.popup:
            self.popup.withdraw()
            self.editor.focus_set()
            
    def on_key_release(self, event):
        """Обрабатывает отпускание клавиши"""
        # Показываем автодополнение только для букв и цифр
        if event.char and (event.char.isalnum() or event.char in '_.'):
            self.editor.after(100, self.show_completions)  # Небольшая задержка
        else:
            self.hide_popup()
            
    def on_popup_key(self, event):
        """Обрабатывает нажатия клавиш в окне автодополнения"""
        if event.keysym == 'Up':
            if self.current_completion > 0:
                self.current_completion -= 1
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(self.current_completion)
                self.listbox.see(self.current_completion)
            return 'break'
        elif event.keysym == 'Down':
            if self.current_completion < self.listbox.size() - 1:
                self.current_completion += 1
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(self.current_completion)
                self.listbox.see(self.current_completion)
            return 'break'
        elif event.keysym in ('Return', 'Tab'):
            self.on_select()
            # После выбора предложения, генерируем событие Return для редактора
            if event.keysym == 'Return':
                self.editor.event_generate('<Return>')
            return 'break'
        elif event.keysym == 'Escape':
            self.hide_popup()
            return 'break'
        else:
            # Если нажата любая другая клавиша, скрываем окно
            self.hide_popup()
            # Безопасно вставляем символ напрямую
            if event.char and event.char.isprintable():
                self.editor.insert(tk.INSERT, event.char)
            return 'break'
            
    def on_select(self, event=None):
        """Выбирает текущее предложение"""
        if not self.completions or self.current_completion >= len(self.completions):
            self.hide_popup()
            return
            
        completion = self.completions[self.current_completion]
        
        # Получаем текущее слово
        current_word, word_start, word_end = self.get_current_word()
        
        # Получаем позицию курсора
        cursor_pos = self.editor.index(tk.INSERT)
        line, col = map(int, cursor_pos.split('.'))
        
        # Удаляем текущее слово
        self.editor.delete(f"{line}.{word_start}", f"{line}.{word_end}")
        
        # Вставляем выбранное предложение
        self.editor.insert(f"{line}.{word_start}", completion)
        
        # Если это функция, добавляем скобки
        if completion in self.builtin_functions and '(' not in completion:
            self.editor.insert(tk.INSERT, "()")
            # Перемещаем курсор внутрь скобок
            self.editor.mark_set(tk.INSERT, f"{line}.{word_start + len(completion) + 1}")
        
        self.hide_popup() 