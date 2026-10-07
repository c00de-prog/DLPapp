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
from i18n import AppError, load_language, save_language, translate
from core import app_dir, validate_url, qualities, probe_command, download_command, progress

BG, CARD, FG, MUTED, GREEN = '#0c111b', '#151d2c', '#eef3fb', '#a3afc2', '#44dcaa'


class DLPapp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.language = load_language()
        self.text_widgets = []
        self._status_key, self._status_values = 'idle', {}
        self.title(self.t('window'))
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
        self.status = tk.StringVar(value=self.t('idle'))
        self.title_text = tk.StringVar(value=self.t('no_video'))
        self.meta = tk.StringVar(value=self.t('quality_hint'))
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
        self._label(box, 'subtitle', bg=BG, fg=MUTED, font=('Segoe UI', 11)).pack(anchor='w', pady=(0, 22))
        self._label(box, 'url_label', bg=BG, fg=GREEN, font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.entry = tk.Entry(box, textvariable=self.url, bg=CARD, fg=FG, insertbackground=GREEN,
                              relief='flat', font=('Segoe UI', 12))
        self.entry.pack(fill='x', ipady=11, pady=(9, 10))
        self.entry.bind('<Return>', lambda e: self._probe())
        self.check = self._button(box, 'check', self._probe)
        self.check.pack(fill='x')
        card = tk.Frame(box, bg=CARD, padx=16, pady=14)
        card.pack(fill='x', pady=(20, 18))
        tk.Label(card, textvariable=self.title_text, bg=CARD, fg=FG, font=('Segoe UI', 12, 'bold'),
                 wraplength=500, justify='left', anchor='w').pack(fill='x')
        tk.Label(card, textvariable=self.meta, bg=CARD, fg=MUTED, font=('Segoe UI', 10),
                 wraplength=500, justify='left').pack(anchor='w', pady=(6, 0))
        self._label(box, 'quality_label', bg=BG, fg=GREEN, font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.combo = ttk.Combobox(box, textvariable=self.quality, state='disabled', font=('Segoe UI', 11))
        self.combo.pack(fill='x', pady=(9, 12))
        row = tk.Frame(box, bg=BG)
        row.pack(fill='x')
        self.download = self._button(row, 'download', self._download)
        self.download.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.download.config(state='disabled')
        self.stop = self._button(row, 'cancel', self._stop, secondary=True)
        self.stop.pack(side='right')
        self.stop.config(state='disabled')
        self.bar = ttk.Progressbar(box, maximum=100)
        self.bar.pack(fill='x', pady=(19, 8))
        tk.Label(box, textvariable=self.status, bg=BG, fg=MUTED, font=('Segoe UI', 10),
                 wraplength=530, justify='left').pack(anchor='w')
        self.folder_button = tk.Button(box, text=self.t('folder_button'), command=self._open_folder, bg=BG, fg=GREEN,
                  activebackground=BG, activeforeground=FG, relief='flat', cursor='hand2',
                  font=('Segoe UI', 10))
        self.folder_button.pack(anchor='w', pady=(12, 0))
        self.text_widgets.append((self.folder_button, 'folder_button'))
        self.language_choice = tk.StringVar(value='Русский' if self.language == 'ru' else 'English')
        selector = ttk.Combobox(header, textvariable=self.language_choice, values=['English', 'Русский'],
                                state='readonly', width=9, font=('Segoe UI', 10))
        selector.pack(side='right')
        selector.bind('<<ComboboxSelected>>', self._change_language)
        self.entry.focus_set()

    def _button(self, parent, key, command, secondary=False):
        widget = tk.Button(parent, text=self.t(key), command=command, bg=CARD if secondary else GREEN,
                         fg=FG if secondary else BG, activebackground='#6ce8bd', activeforeground=BG,
                         disabledforeground=MUTED, relief='flat', padx=16, pady=10,
                         cursor='hand2', font=('Segoe UI', 11, 'bold'))
        self.text_widgets.append((widget, key))
        return widget

    def t(self, key, **values):
        return translate(self.language, key, **values)

    def _label(self, parent, key, **options):
        widget = tk.Label(parent, text=self.t(key), **options)
        self.text_widgets.append((widget, key))
        return widget

    def set_status(self, key, **values):
        self._status_key, self._status_values = key, values
        self.status.set(self.t(key, **values))

    def _error_text(self, error):
        return error.localized(self.language) if isinstance(error, AppError) else str(error)

    def _change_language(self, _event=None):
        self.language = 'ru' if self.language_choice.get() == 'Русский' else 'en'
        self.title(self.t('window'))
        for widget, key in self.text_widgets:
            widget.config(text=self.t(key))
        self.status.set(self.t(self._status_key, **self._status_values))
        if not self.verified_url:
            self.title_text.set(self.t('no_video'))
            self.meta.set(self.t('quality_hint'))
        try:
            save_language(self.language)
        except OSError:
            messagebox.showerror(self.t('error_title'), self.t('settings_error'))

    def _invalidate(self, *_):
        self.verified_url = None
        self.heights = []
        self.combo.config(state='disabled', values=[])
        self.quality.set('')
        self.download.config(state='disabled')
        self.title_text.set(self.t('no_video'))
        self.meta.set(self.t('quality_hint'))

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
                    self.events.put(('status', 'merging'))
            code = proc.wait()
            if self.cancel.is_set():
                result = ('cancelled', None)
            elif code:
                raise RuntimeError('\n'.join(tail)[-2500:]) if tail else AppError('process_exit', code=code)
            elif kind == 'probe':
                # Warnings may precede JSON because stderr shares the output pipe.
                info = next((json.loads(x) for x in reversed(lines) if x.startswith('{')), None)
                if info is None:
                    raise AppError('no_metadata')
                result = ('ready', (url, info, qualities(info)))
            elif final_file and Path(final_file).is_file():
                result = ('done', final_file)
            else:
                raise AppError('missing_output')
        except Exception as exc:
            result = ('cancelled', None) if self.cancel.is_set() else ('error', exc)
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
            self.set_status('checking')
            self._start(command, 'probe', url)
        except Exception as exc:
            messagebox.showerror(self.t('check_error'), self._error_text(exc))

    def _download(self):
        if self.busy or not self.verified_url:
            return
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            height = self.heights[self.combo.current()]
            command = download_command(self.root_dir, self.verified_url, height, self.folder)
            self.set_status('starting')
            self._start(command, 'download', self.verified_url)
        except Exception as exc:
            messagebox.showerror(self.t('download_error'), self._error_text(exc))

    def _poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == 'progress':
                    self.bar['value'] = data[0]
                    self.set_status('progress', percent=f'{data[0]:.1f}', detail=data[1])
                    continue
                if kind == 'status':
                    self.set_status(data)
                    continue
                self.bar.stop()
                self.bar.config(mode='determinate')
                if kind == 'ready':
                    self.verified_url, info, self.heights = data
                    self.title_text.set(info.get('title') or self.t('video'))
                    duration = info.get('duration')
                    length = f'{int(duration)//60}:{int(duration)%60:02d}' if duration else '—'
                    self.meta.set(f"{info.get('uploader') or info.get('extractor') or self.t('video')} · {length}")
                    self.combo['values'] = [f'{h}p' for h in self.heights]
                    self.combo.current(0)
                    self.set_status('ready')
                elif kind == 'done':
                    self.bar['value'] = 100
                    self.set_status('done', name=Path(data).name)
                elif kind == 'cancelled':
                    self.bar['value'] = 0
                    self.set_status('cancelled')
                elif kind == 'error':
                    self.set_status('failed')
                    messagebox.showerror(self.t('error_title'), self._error_text(data))
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
        self.set_status('stopping')
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
            messagebox.showerror(self.t('folder_title'), self._error_text(exc))

    def _close(self):
        if self.busy:
            if not messagebox.askyesno(self.t('close_title'), self.t('close_question')):
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
