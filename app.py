import json
import ctypes
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections import deque
from pathlib import Path
from tkinter import ttk, messagebox
from core import app_dir, validate_url, qualities, probe_command, download_command, progress

BG, CARD, FG, MUTED, GREEN = '#0c111b', '#151d2c', '#eef3fb', '#a3afc2', '#44dcaa'


class DLPapp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('DLPapp • Video downloader')
        self.geometry('650x620')
        self.minsize(570, 600)
        self.configure(bg=BG)
        self.root_dir = app_dir()
        self.folder = self.root_dir / 'Downloads'
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.process = None
        self.process_lock = threading.Lock()
        self.busy = False
        self.verified_url = None
        self.heights = []
        self.url = tk.StringVar()
        self.quality = tk.StringVar()
        self.status = tk.StringVar(value='Вставьте ссылку, чтобы начать.')
        self.title_text = tk.StringVar(value='Видео ещё не выбрано')
        self.meta = tk.StringVar(value='Качества появятся после проверки')
        self.logo = tk.PhotoImage(file=str(Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'assets' / 'logo.png'))
        self.iconphoto(True, self.logo)
        self.header_logo = self.logo.subsample(4, 4)
        self._build()
        self.url.trace_add('write', self._invalidate)
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.after(80, self._poll)

    def _build(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground=CARD, background=CARD, foreground=FG,
                        arrowcolor=GREEN, padding=8, borderwidth=0)
        style.map('TCombobox', fieldbackground=[('readonly', CARD)], foreground=[('readonly', FG)])
        self.option_add('*TCombobox*Listbox.background', CARD)
        self.option_add('*TCombobox*Listbox.foreground', FG)
        style.configure('Horizontal.TProgressbar', background=GREEN, troughcolor=CARD, borderwidth=0)
        box = tk.Frame(self, bg=BG, padx=32, pady=26)
        box.pack(fill='both', expand=True)
        header = tk.Frame(box, bg=BG)
        header.pack(fill='x')
        tk.Label(header, image=self.header_logo, bg=BG).pack(side='left', padx=(0, 12))
        tk.Label(header, text='DLPapp', bg=BG, fg=FG, font=('Segoe UI', 28, 'bold')).pack(side='left')
        tk.Label(box, text='Ссылка. Качество. Готово.', bg=BG, fg=MUTED, font=('Segoe UI', 11)).pack(anchor='w', pady=(0, 22))
        tk.Label(box, text='01  ССЫЛКА НА ВИДЕО', bg=BG, fg=GREEN, font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.entry = tk.Entry(box, textvariable=self.url, bg=CARD, fg=FG, insertbackground=GREEN,
                              relief='flat', font=('Segoe UI', 12))
        self.entry.pack(fill='x', ipady=11, pady=(9, 10))
        self.entry.bind('<Return>', lambda e: self._probe())
        self.check = self._button(box, 'Проверить видео', self._probe)
        self.check.pack(fill='x')
        card = tk.Frame(box, bg=CARD, padx=16, pady=14)
        card.pack(fill='x', pady=(20, 18))
        tk.Label(card, textvariable=self.title_text, bg=CARD, fg=FG, font=('Segoe UI', 12, 'bold'),
                 wraplength=500, justify='left', anchor='w').pack(fill='x')
        tk.Label(card, textvariable=self.meta, bg=CARD, fg=MUTED, font=('Segoe UI', 10),
                 wraplength=500, justify='left').pack(anchor='w', pady=(6, 0))
        tk.Label(box, text='02  КАЧЕСТВО', bg=BG, fg=GREEN, font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.combo = ttk.Combobox(box, textvariable=self.quality, state='disabled', font=('Segoe UI', 11))
        self.combo.pack(fill='x', pady=(9, 12))
        row = tk.Frame(box, bg=BG)
        row.pack(fill='x')
        self.download = self._button(row, 'Скачать видео', self._download)
        self.download.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.download.config(state='disabled')
        self.stop = self._button(row, 'Отмена', self._stop, secondary=True)
        self.stop.pack(side='right')
        self.stop.config(state='disabled')
        self.bar = ttk.Progressbar(box, maximum=100)
        self.bar.pack(fill='x', pady=(19, 8))
        tk.Label(box, textvariable=self.status, bg=BG, fg=MUTED, font=('Segoe UI', 10),
                 wraplength=530, justify='left').pack(anchor='w')
        tk.Button(box, text='Открыть папку Downloads ↗', command=self._open_folder, bg=BG, fg=GREEN,
                  activebackground=BG, activeforeground=FG, relief='flat', cursor='hand2',
                  font=('Segoe UI', 10)).pack(anchor='w', pady=(12, 0))
        self.entry.focus_set()

    @staticmethod
    def _button(parent, text, command, secondary=False):
        return tk.Button(parent, text=text, command=command, bg=CARD if secondary else GREEN,
                         fg=FG if secondary else BG, activebackground='#6ce8bd', activeforeground=BG,
                         disabledforeground=MUTED, relief='flat', padx=16, pady=10,
                         cursor='hand2', font=('Segoe UI', 11, 'bold'))

    def _invalidate(self, *_):
        self.verified_url = None
        self.heights = []
        self.combo.config(state='disabled', values=[])
        self.quality.set('')
        self.download.config(state='disabled')
        self.title_text.set('Видео ещё не выбрано')
        self.meta.set('Качества появятся после проверки')

    def _set_busy(self, value):
        self.busy = value
        self.entry.config(state='disabled' if value else 'normal')
        self.check.config(state='disabled' if value else 'normal')
        self.stop.config(state='normal' if value else 'disabled')
        ready = bool(self.verified_url and self.heights)
        self.combo.config(state='readonly' if ready and not value else 'disabled')
        self.download.config(state='normal' if ready and not value else 'disabled')

    def _start(self, command, kind, url):
        self.cancel.clear()
        self._set_busy(True)
        self.bar.config(mode='indeterminate' if kind == 'probe' else 'determinate', value=0)
        if kind == 'probe':
            self.bar.start(10)
        threading.Thread(target=self._worker, args=(command, kind, url), daemon=True).start()

    def _worker(self, command, kind, url):
        proc = None
        result = None
        try:
            kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding='utf-8', errors='replace', bufsize=1)
            if os.name == 'nt':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            if os.name == 'nt' and getattr(sys, 'frozen', False):
                # Do not leak the GUI bundle's DLL search path into yt-dlp/FFmpeg.
                ctypes.windll.kernel32.SetDllDirectoryW(None)
            try:
                proc = subprocess.Popen(command, **kwargs)
            finally:
                if os.name == 'nt' and getattr(sys, 'frozen', False):
                    ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))
            with self.process_lock:
                self.process = proc
            if self.cancel.is_set():
                self._terminate(proc)
            lines, tail, final_file = [], deque(maxlen=12), None
            for raw in proc.stdout:
                line = raw.strip()
                tail.append(line)
                if kind == 'probe':
                    lines.append(line)
                elif line.startswith('FILE:'):
                    final_file = line[5:]
                elif line.startswith('PROGRESS:'):
                    item = progress(line)
                    if item:
                        self.events.put(('progress', item))
                elif '[Merger]' in line or '[VideoRemuxer]' in line:
                    self.events.put(('status', 'Объединяю видео и звук…'))
            code = proc.wait()
            if self.cancel.is_set():
                result = ('cancelled', None)
            elif code:
                raise RuntimeError('\n'.join(tail)[-2500:] or f'yt-dlp завершился с кодом {code}')
            elif kind == 'probe':
                # Warnings may precede JSON because stderr shares the output pipe.
                info = next((json.loads(x) for x in reversed(lines) if x.startswith('{')), None)
                if info is None:
                    raise ValueError('Сервис не вернул сведения о видео.')
                result = ('ready', (url, info, qualities(info)))
            elif final_file and Path(final_file).is_file():
                result = ('done', final_file)
            else:
                raise RuntimeError('Загрузка завершилась, но готовый файл не найден.')
        except Exception as exc:
            result = ('cancelled', None) if self.cancel.is_set() else ('error', str(exc))
        finally:
            if proc and proc.poll() is None:
                self._terminate(proc)
                proc.wait()
            if proc and proc.stdout:
                proc.stdout.close()
            with self.process_lock:
                self.process = None
            self.events.put(result)

    def _probe(self):
        if self.busy:
            return
        try:
            url = validate_url(self.url.get())
            command = probe_command(self.root_dir, url)
            self._invalidate()
            self.status.set('Проверяю доступность видео…')
            self._start(command, 'probe', url)
        except Exception as exc:
            messagebox.showerror('Не удалось проверить', str(exc))

    def _download(self):
        if self.busy or not self.verified_url:
            return
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            height = self.heights[self.combo.current()]
            command = download_command(self.root_dir, self.verified_url, height, self.folder)
            self.status.set('Начинаю скачивание…')
            self._start(command, 'download', self.verified_url)
        except Exception as exc:
            messagebox.showerror('Не удалось скачать', str(exc))

    def _poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == 'progress':
                    self.bar['value'] = data[0]
                    self.status.set(f'{data[0]:.1f}% · {data[1]}')
                    continue
                if kind == 'status':
                    self.status.set(data)
                    continue
                self.bar.stop()
                self.bar.config(mode='determinate')
                if kind == 'ready':
                    self.verified_url, info, self.heights = data
                    self.title_text.set(info.get('title') or 'Видео')
                    duration = info.get('duration')
                    length = f'{int(duration)//60}:{int(duration)%60:02d}' if duration else '—'
                    self.meta.set(f"{info.get('uploader') or info.get('extractor') or 'Видео'} · {length}")
                    self.combo['values'] = [f'{h}p' for h in self.heights]
                    self.combo.current(0)
                    self.status.set('Видео доступно. Выберите качество.')
                elif kind == 'done':
                    self.bar['value'] = 100
                    self.status.set('Готово! ' + Path(data).name)
                elif kind == 'cancelled':
                    self.bar['value'] = 0
                    self.status.set('Остановлено. Частичные файлы сохранены для повторной загрузки.')
                elif kind == 'error':
                    self.status.set('Не удалось завершить операцию. Можно повторить.')
                    messagebox.showerror('Ошибка', data)
                self._set_busy(False)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    @staticmethod
    def _terminate(proc):
        if proc.poll() is not None:
            return
        try:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                               creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True, timeout=10)
            else:
                proc.terminate()
        except (OSError, subprocess.TimeoutExpired):
            try:
                proc.kill()
            except OSError:
                pass

    def _stop(self):
        self.cancel.set()
        self.stop.config(state='disabled')
        self.status.set('Останавливаю…')
        with self.process_lock:
            proc = self.process
        if proc:
            threading.Thread(target=self._terminate, args=(proc,), daemon=True).start()

    def _open_folder(self):
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            if os.name == 'nt':
                os.startfile(str(self.folder))
            else:
                subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(self.folder)])
        except Exception as exc:
            messagebox.showerror('Папка', str(exc))

    def _close(self):
        if self.busy:
            if not messagebox.askyesno('Закрыть?', 'Остановить текущую операцию и закрыть приложение?'):
                return
            self._stop()
            self.after(100, self._close_when_stopped)
        else:
            self.destroy()

    def _close_when_stopped(self):
        if self.busy:
            self.after(100, self._close_when_stopped)
        else:
            self.destroy()


if __name__ == '__main__':
    import sys
    DLPapp().mainloop()
