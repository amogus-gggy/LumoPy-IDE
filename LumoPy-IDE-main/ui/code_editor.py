import tkinter as tk
from tkinter import Text, Scrollbar
from pygments import lex
from pygments.lexers import PythonLexer, get_lexer_by_name, TextLexer
from pygments.token import Token
from ui.simple_autocomplete import SimpleAutocomplete
import time
import os

class CodeEditor(Text):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.config(font=("Consolas", 12), undo=True, wrap="none", bg="#1e1e1e", fg="#ffffff", insertbackground="#ffffff")
        
        # Привязки событий для подсветки синтаксиса
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<KeyPress>", self._on_key_press)
        self.bind("<ButtonRelease-1>", self._on_mouse_release)
        
        # Привязки для вставки текста
        self.bind("<<Paste>>", self._on_paste)
        self.bind("<<Undo>>", self._on_undo_redo)
        self.bind("<<Redo>>", self._on_undo_redo)
        
        # Привязка для изменения содержимого
        self.bind("<<Modified>>", self._on_modified)
        
        # Привязка для вставки через контекстное меню
        self.bind("<Button-3>", self._on_right_click)
        
        # Привязки для автодополнения и автоотступа
        self.bind("<Return>", self._on_return)
        self.bind("(", lambda e: self._auto_pair('(', ')'))
        self.bind("[", lambda e: self._auto_pair('[', ']'))
        self.bind("{", lambda e: self._auto_pair('{', '}'))
        self.bind('"', lambda e: self._auto_pair('"', '"'))
        self.bind("'", lambda e: self._auto_pair("'", "'"))
        
        # Инициализируем простое автодополнение
        self.autocomplete = SimpleAutocomplete(self)
        
        # Определяем тип файла
        self.file_extension = None
        self.lexer = PythonLexer()
        
        # Переменные для оптимизации подсветки
        self._highlight_after_id = None
        self._highlight_delay = 500  # миллисекунды (увеличено с 300)
        
        self._highlight()
        # Добавляю тёмный скроллбар
        self.scrollbar = Scrollbar(master, command=self.yview, bg="#222", troughcolor="#111", activebackground="#444", highlightbackground="#111")
        self['yscrollcommand'] = self.scrollbar.set

    def set_file_extension(self, extension):
        """Устанавливает расширение файла для правильной подсветки синтаксиса"""
        self.file_extension = extension
        if extension:
            try:
                if extension.lower() in ['.py', '.pyw']:
                    self.lexer = PythonLexer()
                elif extension.lower() in ['.js', '.javascript']:
                    self.lexer = get_lexer_by_name('javascript')
                elif extension.lower() in ['.html', '.htm']:
                    self.lexer = get_lexer_by_name('html')
                elif extension.lower() in ['.css']:
                    self.lexer = get_lexer_by_name('css')
                elif extension.lower() in ['.json']:
                    self.lexer = get_lexer_by_name('json')
                elif extension.lower() in ['.xml']:
                    self.lexer = get_lexer_by_name('xml')
                elif extension.lower() in ['.sql']:
                    self.lexer = get_lexer_by_name('sql')
                elif extension.lower() in ['.md', '.markdown']:
                    self.lexer = get_lexer_by_name('markdown')
                elif extension.lower() in ['.txt', '.text']:
                    self.lexer = TextLexer()
                else:
                    # Пытаемся определить по расширению
                    self.lexer = get_lexer_by_name(extension.lower()[1:])
            except:
                # Если не удалось определить, используем текстовый лексер
                self.lexer = TextLexer()
        else:
            # Если расширение не указано, используем Python по умолчанию
            self.lexer = PythonLexer()
        self._highlight()

    def _highlight(self, event=None):
        try:
            code = self.get("1.0", tk.END)
            if not code.strip():  # Если код пустой, не подсвечиваем
                return
                
            # Очищаем все существующие теги
            self.tag_remove("Token", "1.0", tk.END)
            
            # Устанавливаем начальную позицию
            self.mark_set("range_start", "1.0")
            
            # Используем текущий лексер для подсветки
            for token, content in lex(code, self.lexer):
                if content:  # Проверяем, что контент не пустой
                    self.mark_set("range_end", f"range_start + {len(content)}c")
                    self.tag_add(str(token), "range_start", "range_end")
                    self.mark_set("range_start", "range_end")
                    
            # Применяем теги
            self._set_tags()
            
        except Exception as e:
            # Если подсветка не удалась, не делаем ничего
            # Можно добавить логирование ошибки для отладки
            print(f"Ошибка подсветки: {e}")
            pass

    def _set_tags(self):
        """Настройка цветовой схемы для Python"""
        
        # Основные токены Python
        self.tag_configure(str(Token.Keyword), foreground="#569CD6")  # import, from, class, def, if, else, etc.
        self.tag_configure(str(Token.Keyword.Namespace), foreground="#569CD6")  # import, from
        self.tag_configure(str(Token.Keyword.Type), foreground="#569CD6")  # class, def
        self.tag_configure(str(Token.Keyword.Constant), foreground="#569CD6")  # True, False, None
        
        # Встроенные функции и классы
        self.tag_configure(str(Token.Name.Builtin), foreground="#4EC9B0")  # print, len, str, etc.
        self.tag_configure(str(Token.Name.Builtin.Pseudo), foreground="#4EC9B0")  # self, cls
        
        # Строки
        self.tag_configure(str(Token.Literal.String), foreground="#D69D85")
        self.tag_configure(str(Token.Literal.String.Single), foreground="#D69D85")
        self.tag_configure(str(Token.Literal.String.Double), foreground="#D69D85")
        self.tag_configure(str(Token.Literal.String.Triple), foreground="#D69D85")
        self.tag_configure(str(Token.Literal.String.Doc), foreground="#D69D85")
        self.tag_configure(str(Token.Literal.String.Escape), foreground="#D69D85")
        
        # Комментарии
        self.tag_configure(str(Token.Comment), foreground="#6A9955")
        self.tag_configure(str(Token.Comment.Single), foreground="#6A9955")
        self.tag_configure(str(Token.Comment.Multiline), foreground="#6A9955")
        self.tag_configure(str(Token.Comment.Preproc), foreground="#6A9955")
        
        # Операторы
        self.tag_configure(str(Token.Operator), foreground="#B4B4B4")
        self.tag_configure(str(Token.Operator.Word), foreground="#B4B4B4")  # and, or, not, in, is
        
        # Функции и классы
        self.tag_configure(str(Token.Name.Function), foreground="#DCDCAA")
        self.tag_configure(str(Token.Name.Class), foreground="#4EC9B0")
        self.tag_configure(str(Token.Name.Decorator), foreground="#DCDCAA")  # @decorator
        
        # Переменные и атрибуты
        self.tag_configure(str(Token.Name), foreground="#FFFFFF")
        self.tag_configure(str(Token.Name.Variable), foreground="#FFFFFF")
        self.tag_configure(str(Token.Name.Attribute), foreground="#9CDCFE")
        
        # Числа
        self.tag_configure(str(Token.Literal.Number), foreground="#B5CEA8")
        self.tag_configure(str(Token.Literal.Number.Integer), foreground="#B5CEA8")
        self.tag_configure(str(Token.Literal.Number.Float), foreground="#B5CEA8")
        self.tag_configure(str(Token.Literal.Number.Hex), foreground="#B5CEA8")
        self.tag_configure(str(Token.Literal.Number.Oct), foreground="#B5CEA8")
        self.tag_configure(str(Token.Literal.Number.Bin), foreground="#B5CEA8")
        
        # Специальные токены
        self.tag_configure(str(Token.Literal), foreground="#D69D85")
        self.tag_configure(str(Token.Punctuation), foreground="#B4B4B4")
        self.tag_configure(str(Token.Text), foreground="#FFFFFF")
        self.tag_configure(str(Token.Text.Whitespace), foreground="#FFFFFF")
        
        # Дополнительные Python токены
        self.tag_configure(str(Token.Name.Exception), foreground="#569CD6")
        self.tag_configure(str(Token.Name.Label), foreground="#569CD6")
        self.tag_configure(str(Token.Name.Entity), foreground="#569CD6")
        
        # Специальные символы
        self.tag_configure(str(Token.Punctuation.Marker), foreground="#B4B4B4")
        self.tag_configure(str(Token.Punctuation.Indicator), foreground="#B4B4B4")
        
        # Обработка ошибок
        self.tag_configure(str(Token.Error), foreground="#F44747")
        self.tag_configure(str(Token.Error.Token), foreground="#F44747")
        
        # Дополнительные токены
        self.tag_configure(str(Token.Generic), foreground="#FFFFFF")
        self.tag_configure(str(Token.Generic.Deleted), foreground="#F44747")
        self.tag_configure(str(Token.Generic.Emph), foreground="#FFFFFF")
        self.tag_configure(str(Token.Generic.Error), foreground="#F44747")
        self.tag_configure(str(Token.Generic.Heading), foreground="#569CD6")
        self.tag_configure(str(Token.Generic.Inserted), foreground="#6A9955")

    def _on_key_release(self, event=None):
        # Не запускаем подсветку при навигации стрелками
        if event and event.keysym in ['Up', 'Down', 'Left', 'Right', 'Home', 'End', 'Page_Up', 'Page_Down']:
            return
            
        # Не запускаем подсветку если содержимое не изменилось
        if not self.edit_modified():
            return
            
        # Немедленная подсветка для некоторых символов
        if event and event.char in ['(', ')', '[', ']', '{', '}', '"', "'", ':', ';', '#']:
            self._highlight()
            return
        
        # Отменяем предыдущий запрос на подсветку
        if self._highlight_after_id:
            self.after_cancel(self._highlight_after_id)
        
        # Планируем новую подсветку с задержкой
        self._highlight_after_id = self.after(self._highlight_delay, self._highlight)

    def _on_key_press(self, event=None):
        # Не запускаем подсветку при навигации стрелками
        if event and event.keysym in ['Up', 'Down', 'Left', 'Right', 'Home', 'End', 'Page_Up', 'Page_Down']:
            return
            
        # Немедленная подсветка для некоторых символов
        if event and event.char in ['(', ')', '[', ']', '{', '}', '"', "'", ':', ';', '#']:
            self._highlight()
            return
        
        # Отменяем предыдущий запрос на подсветку
        if self._highlight_after_id:
            self.after_cancel(self._highlight_after_id)
        
        # Планируем новую подсветку с задержкой
        self._highlight_after_id = self.after(self._highlight_delay, self._highlight)

    def _on_mouse_release(self, event=None):
        """Обработчик отпускания кнопки мыши"""
        # Отменяем предыдущий запрос на подсветку
        if self._highlight_after_id:
            self.after_cancel(self._highlight_after_id)
        
        # Планируем новую подсветку с задержкой
        self._highlight_after_id = self.after(self._highlight_delay, self._highlight)

    def _on_return(self, event=None):
        # Если открыт autocomplete, не делать автоотступ
        if hasattr(self.autocomplete, 'popup') and self.autocomplete.popup and self.autocomplete.popup.winfo_exists():
            return None  # Дать обработать _autocomplete_select

        # Получаем номер текущей строки
        index = self.index("insert")
        line_num = int(index.split('.')[0])

        # Ищем предыдущую непустую строку для определения базового отступа
        prev_indent = ''
        for n in range(line_num, 0, -1):
            prev_line = self.get(f"{n}.0", f"{n}.end")
            if prev_line.strip() != '':
                for char in prev_line:
                    if char in (' ', '\t'):
                        prev_indent += char
                    else:
                        break
                break

        # Получаем текущую строку
        line_start = f"{line_num}.0"
        line = self.get(line_start, f"{line_num}.end")

        # Если строка заканчивается на : (или (, [, {) — увеличиваем отступ
        if line.rstrip().endswith((':', '(', '[', '{')):
            prev_indent += "    "  # 4 пробела

        self.insert("insert", "\n" + prev_indent)
        return "break"

    def _auto_pair(self, open_char, close_char):
        self.insert("insert", open_char + close_char)
        self.mark_set("insert", "insert -1c")
        return "break"
        
    def _trigger_autocomplete(self, event=None):
        """Принудительно запускает автодополнение"""
        self.autocomplete.show_completions()
        return "break"
        
    def _hide_autocomplete(self, event=None):
        """Скрывает автодополнение"""
        self.autocomplete.hide_popup()
        
    def force_highlight(self):
        """Принудительно запускает подсветку синтаксиса"""
        if self._highlight_after_id:
            self.after_cancel(self._highlight_after_id)
        self._highlight()
        
    def schedule_highlight(self, delay=None):
        """Планирует подсветку с указанной задержкой"""
        if self._highlight_after_id:
            self.after_cancel(self._highlight_after_id)
        
        if delay is None:
            delay = self._highlight_delay
            
        self._highlight_after_id = self.after(delay, self._highlight)

    def _on_paste(self, event=None):
        """Обработчик вставки текста"""
        # Отменяем предыдущий запрос на подсветку
        if self._highlight_after_id:
            self.after_cancel(self._highlight_after_id)
        
        # Планируем новую подсветку с небольшой задержкой
        self._highlight_after_id = self.after(100, self._highlight)

    def _on_undo_redo(self, event=None):
        """Обработчик отмены/повтора действий"""
        # Отменяем предыдущий запрос на подсветку
        if self._highlight_after_id:
            self.after_cancel(self._highlight_after_id)
        
        # Планируем новую подсветку с небольшой задержкой
        self._highlight_after_id = self.after(100, self._highlight)

    def _on_modified(self, event=None):
        """Обработчик изменения содержимого"""
        # Проверяем, было ли изменение
        if self.edit_modified():
            # Сбрасываем флаг изменения
            self.edit_modified(False)
            
            # Отменяем предыдущий запрос на подсветку
            if self._highlight_after_id:
                self.after_cancel(self._highlight_after_id)
            
            # Планируем новую подсветку с задержкой
            self._highlight_after_id = self.after(200, self._highlight)

    def _on_right_click(self, event=None):
        """Обработчик правого клика мыши"""
        # Планируем подсветку после возможной вставки через контекстное меню
        self.after(200, self._highlight) 