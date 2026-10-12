"""Lazy, searchable offline help panel with selectable, scrollable answers."""
import tkinter as tk
from tkinter import ttk
from help_content import articles, greeting


class HelpPanel(tk.Frame):
    def __init__(self, parent, language, nickname, bg, fg, muted, accent, font):
        super().__init__(parent, bg=bg)
        self.language, self.nickname = language, nickname
        self.bg, self.fg, self.muted = bg, fg, muted
        self.greeting = tk.Label(self, text=greeting(language, nickname), bg=bg, fg=accent,
                                font=(font, 11, 'bold'), anchor='w', justify='left', wraplength=540)
        self.greeting.pack(fill='x', pady=(0, 8))
        tk.Label(self, text='Поиск по вопросам' if language == 'ru' else 'Search questions',
                 bg=bg, fg=muted, anchor='w').pack(fill='x')
        self.query = tk.StringVar()
        self.search = tk.Entry(self, textvariable=self.query, bg='#1a2934', fg=fg,
                               insertbackground=accent, relief='flat', font=(font, 11))
        self.search.pack(fill='x', ipady=8, pady=(4, 8))
        from clipboard import bind_entry
        from i18n import translate
        bind_entry(self.search, lambda key, **values: translate(language, key, **values))
        question_box = tk.Frame(self, bg=bg)
        question_box.pack(fill='x')
        self.questions = tk.Listbox(question_box, height=5, bg='#141f29', fg=fg,
                                   selectbackground='#204c45', selectforeground=fg,
                                   activestyle='none', exportselection=False, relief='flat',
                                   highlightthickness=0, font=(font, 10))
        question_scroll = ttk.Scrollbar(question_box, command=self.questions.yview)
        self.questions.configure(yscrollcommand=question_scroll.set)
        question_scroll.pack(side='right', fill='y')
        self.questions.pack(side='left', fill='both', expand=True)
        answer_box = tk.Frame(self, bg=bg)
        answer_box.pack(fill='both', expand=True, pady=(10, 0))
        self.answer = tk.Text(answer_box, wrap='word', height=7, bg=bg, fg=fg, relief='flat',
                              highlightthickness=0, font=(font, 11), padx=4, pady=4,
                              spacing3=7, state='disabled')
        answer_scroll = ttk.Scrollbar(answer_box, command=self.answer.yview)
        self.answer.configure(yscrollcommand=answer_scroll.set)
        answer_scroll.pack(side='right', fill='y')
        self.answer.pack(side='left', fill='both', expand=True)
        self.questions.bind('<<ListboxSelect>>', self._show)
        self.query.trace_add('write', self._filter)
        self._filter()

    def refresh_nickname(self, nickname):
        self.nickname = nickname
        self.greeting.configure(text=greeting(self.language, nickname))
        self._show()

    def _filter(self, *_):
        self.rows = articles(self.language, self.query.get())
        self.questions.delete(0, 'end')
        for _, title, _ in self.rows:
            self.questions.insert('end', title)
        if self.rows:
            self.questions.selection_set(0)
        self._show()

    def _show(self, *_):
        selected = self.questions.curselection()
        if selected:
            _, title, body = self.rows[selected[0]]
            value = greeting(self.language, self.nickname) + '\n\n' + title + '\n\n' + body
        else:
            value = 'Ничего не найдено. Попробуйте другой запрос.' if self.language == 'ru' else 'No results. Try another search.'
        self.answer.configure(state='normal')
        self.answer.delete('1.0', 'end')
        self.answer.insert('1.0', value)
        self.answer.configure(state='disabled')
        self.answer.yview_moveto(0)
