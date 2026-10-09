"""Lightweight Tkinter UI. All network/process work happens off the UI thread."""
import ctypes
import json
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from collections import deque
from pathlib import Path
from tkinter import ttk, messagebox, filedialog, font as tkfont
from i18n import AppError, detect_language, translate
from core import app_dir, validate_url, qualities, probe_command, download_command, progress
from media import FORMATS, VIDEO_FORMATS, AUDIO_FORMATS, available_heights
from settings import Settings, atomic_json
from notifications import Tray
from version import VERSION, AUTHOR, GITHUB_URL
import updates
from clipboard import bind_entry, paste
from ui import RoundedButton, Panel, PageStack

FONT = 'Segoe UI' if os.name == 'nt' else 'DejaVu Sans'
BG, CARD, FG, MUTED, GREEN = '#0b1219', '#141f29', '#edf4f8', '#94a4b4', '#17c99a'


class DLPapp(tk.Tk):
    def __init__(self, settings=None, schedule_updates=True):
        super().__init__()
        self.settings = settings or Settings()
        self.language = self.settings.get('language')
        if self.language == 'auto':
            self.language = detect_language()
        self.root_dir = app_dir()
        self.folder = self.settings.folder(self.root_dir)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.process, self.process_lock = None, threading.Lock()
        self.busy = False
        self.kind = None
        self.hidden = False
        self.updating = False
        self.maintenance = False
        self.pending_release = None
        self.update_cancel = threading.Event()
        self.settings_window = None
        self.history_tree = None
        self.download_snapshot = None
        self.verified_url, self.info, self.heights = None, None, []
        self.url, self.quality = tk.StringVar(), tk.StringVar()
        self.format = tk.StringVar(value=self.settings.get('last_format') if self.settings.get('last_format') in FORMATS else 'MP4')
        self.codec = tk.StringVar(value=self.settings.get('last_codec') if self.settings.get('last_codec') in ('auto', 'h264', 'hevc', 'vp9', 'av1') else 'auto')
        self.codec_choice = tk.StringVar()
        self.status, self.title_text, self.meta = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.update_status = tk.StringVar()
        self._status_key, self._status_values = 'idle', {}
        self.text_widgets = []
        self.geometry(f'880x{max(600,min(820,self.winfo_screenheight()-100))}')
        self.minsize(720, 600)
        tkfont.nametofont('TkDefaultFont').configure(family=FONT, size=10)
        tkfont.nametofont('TkTextFont').configure(family=FONT, size=10)
        self.configure(bg=BG)
        self.title(self.t('window'))
        self.resources = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        self.logo = tk.PhotoImage(file=str(self.resources / 'assets/logo.png'))
        self.iconphoto(True, self.logo)
        self.header_logo = self.logo.subsample(5, 5)
        self.tray = Tray(self.events, self.resources / 'assets/icon.ico')
        self._build()
        self._invalidate()
        self.set_status('idle')
        self.url.trace_add('write', self._invalidate)
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.after(80, self._poll)
        self.after(150, self._acknowledge_update)
        if schedule_updates:
            self.after(1500, self._auto_updates)

    def t(self, key, **values):
        return translate(self.language, key, **values)

    def _label(self, parent, key, **options):
        widget = tk.Label(parent, text=self.t(key), bg=options.pop('bg', BG), fg=options.pop('fg', FG),
                          font=options.pop('font', (FONT, 11)), **options)
        self.text_widgets.append((widget, key))
        return widget

    def _button(self, parent, key, command, secondary=False):
        widget = RoundedButton(parent, self.t(key), command, primary=not secondary, font=(FONT,10,'bold'))
        self.text_widgets.append((widget,key))
        return widget

    def _entry(self, parent, variable):
        entry = tk.Entry(parent, textvariable=variable, bg='#1a2934', fg=FG, insertbackground=GREEN,
                         selectbackground=GREEN, selectforeground=BG, relief='flat', highlightthickness=1,
                         highlightbackground='#273c49',highlightcolor=GREEN,font=(FONT, 11))
        bind_entry(entry, self.t)
        return entry

    def _build(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground='#1a2934', background='#1a2934', foreground=FG,
                        arrowcolor=GREEN, bordercolor='#273c49', lightcolor='#273c49', darkcolor='#273c49', padding=9)
        style.map('TCombobox', fieldbackground=[('readonly','#1a2934'),('disabled','#17232d')],
                  foreground=[('disabled',MUTED),('readonly',FG)])
        style.configure('Horizontal.TProgressbar',background=GREEN,troughcolor='#1b2a35',
                        bordercolor='#1b2a35',lightcolor='#1b2a35',darkcolor='#1b2a35',borderwidth=0,thickness=5)
        style.configure('Treeview',background=CARD,fieldbackground=CARD,foreground=FG,rowheight=38,
                        borderwidth=0,relief='flat',font=(FONT,10))
        style.layout('Treeview',[('Treeview.treearea',{'sticky':'nswe'})])
        style.configure('Treeview.Heading',background='#1b2b37',foreground=MUTED,relief='flat',padding=10,font=(FONT,9,'bold'))
        style.map('Treeview',background=[('selected','#204c45')],foreground=[('selected',FG)])
        style.configure('Vertical.TScrollbar',background='#2b3c48',troughcolor=CARD,
                        bordercolor=CARD,lightcolor='#2b3c48',darkcolor='#2b3c48',
                        arrowcolor=MUTED,relief='flat',arrowsize=10)
        style.map('Vertical.TScrollbar',background=[('active','#405764'),('disabled',CARD)],
                  arrowcolor=[('disabled',MUTED)])
        self.option_add('*TCombobox*Listbox.background',CARD)
        self.option_add('*TCombobox*Listbox.foreground',FG)
        self.content_canvas=tk.Canvas(self,bg=BG,highlightthickness=0)
        main_scroll=ttk.Scrollbar(self,orient='vertical',command=self.content_canvas.yview)
        main_scroll.pack(side='right',fill='y')
        self.content_canvas.configure(yscrollcommand=main_scroll.set)
        self.content_canvas.pack(fill='both',expand=True)
        box=tk.Frame(self.content_canvas,bg=BG,padx=4,pady=4)
        self.content_window=self.content_canvas.create_window(0,18,window=box,anchor='n')
        def layout(_event=None):
            width=self.content_canvas.winfo_width()
            self.content_canvas.coords(self.content_window,width/2,18)
            self.content_canvas.itemconfigure(self.content_window,width=max(660,min(860,width-48)))
            self.content_canvas.configure(scrollregion=(0,0,width,max(self.content_canvas.winfo_height(),box.winfo_reqheight()+36)))
        self.content_canvas.bind('<Configure>',layout);box.bind('<Configure>',layout)
        def scroll(event):
            if event.widget.winfo_toplevel()==self:
                self.content_canvas.yview_scroll(-1 if getattr(event,'num',0)==4 else 1 if getattr(event,'num',0)==5 else -int(event.delta/120),'units')
        self.bind_all('<MouseWheel>',scroll);self.bind_all('<Button-4>',scroll);self.bind_all('<Button-5>',scroll)
        header=tk.Frame(box,bg=BG);header.pack(fill='x',pady=(0,16))
        tk.Label(header,image=self.header_logo,bg=BG).pack(side='left',padx=(0,12))
        branding=tk.Frame(header,bg=BG);branding.pack(side='left')
        tk.Label(branding,text='DLPapp',bg=BG,fg=FG,font=(FONT,24,'bold')).pack(anchor='w')
        self.nickname_label=tk.Label(branding,text=self.settings.get('nickname') or self.t('subtitle'),bg=BG,fg=MUTED,font=(FONT,10))
        self.nickname_label.pack(anchor='w')
        self._button(header,'settings',self._settings,True).pack(side='right')
        self._button(header,'downloads',lambda:self._settings('downloads'),True).pack(side='right',padx=8)
        link=Panel(box);link.pack(fill='x',pady=(0,14));body=link.body
        self._label(body,'url_label',bg=CARD,fg=GREEN,font=(FONT,10,'bold')).pack(anchor='w',pady=(0,12))
        row=tk.Frame(body,bg=CARD);row.pack(fill='x')
        self.entry=self._entry(row,self.url);self.entry.pack(side='left',fill='x',expand=True,ipady=12,padx=(0,10))
        self.entry.bind('<Return>',lambda _e:self._probe())
        self.paste_button=self._button(row,'paste',lambda:paste(self.entry),True);self.paste_button.pack(side='left',padx=(0,8))
        self.check=self._button(row,'check',self._probe);self.check.pack(side='right')
        card=Panel(box);card.pack(fill='x',pady=(0,14));body=card.body
        self._label(body,'video_info',bg=CARD,fg=MUTED,font=(FONT,9,'bold')).pack(anchor='w')
        self.video_title_label=tk.Label(body,textvariable=self.title_text,bg=CARD,fg=FG,wraplength=710,
                                      anchor='w',justify='left',font=(FONT,14,'bold'))
        self.video_title_label.pack(fill='x',pady=(10,6))
        tk.Label(body,textvariable=self.meta,bg=CARD,fg=MUTED,font=(FONT,10),anchor='w').pack(fill='x')
        self.video_title_label.bind('<Configure>',lambda e:self.video_title_label.configure(wraplength=max(200,e.width)))
        panel=Panel(box);panel.pack(fill='x',pady=(0,14));body=panel.body
        self._label(body,'options',bg=CARD,fg=GREEN,font=(FONT,10,'bold')).pack(anchor='w',pady=(0,12))
        options=tk.Frame(body,bg=CARD);options.pack(fill='x')
        for i in range(3):options.columnconfigure(i,weight=1,uniform='options')
        combos=[]
        for i,(key,variable,values) in enumerate([('format',self.format,FORMATS),('quality',self.quality,[]),('codec',self.codec_choice,[])]):
            self._label(options,key,bg=CARD,fg=MUTED,font=(FONT,9)).grid(row=0,column=i,sticky='w',padx=(0,12))
            combo=ttk.Combobox(options,textvariable=variable,values=values,state='readonly',width=12,font=(FONT,10))
            combo.grid(row=1,column=i,sticky='ew',padx=(0,12),pady=(7,0));combos.append(combo)
        self.format_combo,self.combo,self.codec_combo=combos
        self.format_combo.bind('<<ComboboxSelected>>',self._options_changed)
        self.codec_combo.bind('<<ComboboxSelected>>',self._options_changed)
        self._label(body,'codec_hint',bg=CARD,fg=MUTED,font=(FONT,9),wraplength=710,justify='left').pack(anchor='w',pady=(12,0))
        progress_panel=Panel(box);progress_panel.pack(fill='x',pady=(0,14));body=progress_panel.body
        row=tk.Frame(body,bg=CARD);row.pack(fill='x')
        self.download=self._button(row,'download',self._download);self.download.pack(side='left',fill='x',expand=True,padx=(0,10))
        self.stop=self._button(row,'cancel',self._stop,True);self.stop.pack(side='right')
        self.bar=ttk.Progressbar(body,maximum=100);self.bar.pack(fill='x',pady=(18,10))
        tk.Label(body,textvariable=self.status,bg=CARD,fg=MUTED,wraplength=710,justify='left',anchor='w',font=(FONT,10)).pack(fill='x')
        footer=tk.Frame(box,bg=BG);footer.pack(fill='x',pady=(2,10))
        self._button(footer,'folder_button',self._open_folder,True).pack(side='left')
        self.background_button=self._button(footer,'background',self._hide,True);self.background_button.pack(side='right')
        tk.Button(box,text='GitHub ↗  ·  '+VERSION,command=lambda:webbrowser.open(GITHUB_URL),bg=BG,fg=MUTED,
                  relief='flat',highlightthickness=0,cursor='hand2',font=(FONT,9)).pack(anchor='e',pady=(0,8))
        self.entry.focus_set();self._options_changed()

    def set_status(self, key, **values):
        self._status_key, self._status_values = key, values
        self.status.set(self.t(key, **values))

    def _error_text(self, error):
        return error.localized(self.language) if isinstance(error, AppError) else str(error)

    def _invalidate(self, *_):
        self.verified_url, self.info, self.heights = None, None, []
        self.combo.config(state='disabled', values=[])
        self.quality.set('')
        self.download.config(state='disabled')
        self.title_text.set(self.t('no_video'))
        self.meta.set(self.t('quality_hint'))

    def _options_changed(self, _event=None):
        fmt = self.format.get()
        if _event is not None and _event.widget == self.codec_combo:
            self.codec.set(self.codec_keys[self.codec_combo.current()])
        allowed = ['auto', 'h264', 'hevc', 'av1'] if fmt == 'MP4' else ['auto', 'vp9', 'av1'] if fmt == 'WEBM' else ['auto', 'h264', 'hevc', 'vp9', 'av1']
        if self.codec.get() not in allowed:
            self.codec.set('auto')
        names = dict(auto=self.t('auto'), h264='H.264', hevc='HEVC', vp9='VP9', av1='AV1')
        self.codec_keys = allowed
        self.codec_combo.config(values=[names[x] for x in allowed])
        self.codec_choice.set(names[self.codec.get()])
        if self.info:
            previous = self.quality.get()
            self.heights = available_heights(self.info, fmt, self.codec.get())
            if fmt in AUDIO_FORMATS:
                self.quality.set(self.t('audio_only'))
                self.combo.config(values=[])
            else:
                options = [f'{x}p' for x in self.heights]
                self.combo.config(values=options)
                saved = self.settings.get('last_quality')
                self.quality.set(previous if previous in options else saved if saved in options else options[0] if options else '')
                if not options:
                    self.set_status('no_compatible')
                elif not self.busy:
                    self.set_status('ready')
        self._set_busy(self.busy)

    def _set_busy(self, value):
        self.busy = value
        blocked = value or self.maintenance or self.updating
        ready = self.verified_url and (self.heights or self.format.get() in AUDIO_FORMATS)
        for widget in (self.entry, self.paste_button, self.check):
            widget.config(state='disabled' if blocked else 'normal')
        self.format_combo.config(state='disabled' if blocked else 'readonly')
        self.codec_combo.config(state='disabled' if blocked or self.format.get() in AUDIO_FORMATS else 'readonly')
        self.combo.config(state='readonly' if ready and not blocked and self.format.get() in VIDEO_FORMATS else 'disabled')
        self.download.config(state='normal' if ready and not blocked else 'disabled')
        self.stop.config(state='normal' if value else 'disabled')
        self.background_button.config(state='normal' if value and self.kind == 'download' else 'disabled')

    def _start(self, command, kind, url):
        self.cancel.clear()
        self.kind = kind
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
                elif any(x in line for x in ('[Merger]', '[VideoRemuxer]', '[ExtractAudio]')):
                    self.events.put(('status', 'processing'))
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
        if self.busy or self.maintenance or self.updating:
            return
        try:
            url = validate_url(self.url.get())
            command = probe_command(self.root_dir, url)
            self._invalidate()
            self.set_status('checking')
            self._start(command, 'probe', url)
        except Exception as exc:
            messagebox.showerror(self.t('check_error'), self._error_text(exc), parent=self)

    def _download(self):
        if self.busy or self.maintenance or self.updating or not self.verified_url:
            return
        try:
            fmt, codec = self.format.get(), self.codec.get()
            height = 0 if fmt in AUDIO_FORMATS else int(self.quality.get().rstrip('p'))
            folder = self.settings.folder(self.root_dir)
            folder.mkdir(parents=True, exist_ok=True)
            command = download_command(self.root_dir, self.verified_url, height, folder, fmt, codec)
            self.settings.update(last_format=fmt, last_codec=codec, last_quality=self.quality.get())
            self.download_snapshot = dict(folder=folder, title=self.info.get('title', ''), url=self.verified_url, fmt=fmt)
            self.folder = folder
            self.set_status('background_hint')
            self._start(command, 'download', self.verified_url)
        except Exception as exc:
            messagebox.showerror(self.t('download_error'), self._error_text(exc), parent=self)

    def _poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == 'restore':
                    self._restore()
                    continue
                if kind.startswith('update_') or kind.startswith('ytdlp_'):
                    self._update_event(kind, data)
                    continue
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
                    self.verified_url, self.info, self.heights = data
                    self.title_text.set(self.info.get('title') or self.t('video'))
                    duration = self.info.get('duration')
                    length = f'{int(duration)//60}:{int(duration)%60:02d}' if isinstance(duration, (int, float)) else '—'
                    self.meta.set(f"{self.info.get('uploader') or self.info.get('extractor') or self.t('video')} · {length}")
                    self._options_changed()
                    self.set_status('ready' if self.heights or self.format.get() in AUDIO_FORMATS else 'no_compatible')
                elif kind == 'done':
                    self.bar['value'] = 100
                    self.set_status('done', name=Path(data).name)
                    try:
                        self.settings.record(data, **self.download_snapshot)
                    except OSError:
                        self.set_status('settings_error')
                    self._refresh_history()
                    self.tray.notify(self.t('notification_done'), Path(data).name)
                    if self.hidden and not self.tray.available:
                        self._restore()
                        messagebox.showinfo('DLPapp', self.t('done', name=Path(data).name), parent=self)
                elif kind == 'cancelled':
                    self.bar['value'] = 0
                    self.set_status('cancelled')
                elif kind == 'error':
                    self.set_status('failed')
                    if self.hidden:
                        self.tray.notify(self.t('notification_error'), self._error_text(data))
                        if not self.tray.available:
                            self._restore()
                    if not self.hidden:
                        messagebox.showerror(self.t('error_title'), self._error_text(data), parent=self)
                self.kind = None
                self._set_busy(False)
        except queue.Empty:
            pass
        if self.winfo_exists():
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

    def _open_path(self, path):
        try:
            path = Path(path)
            if not path.exists():
                raise AppError('file_missing')
            if os.name == 'nt':
                os.startfile(str(path))
            else:
                subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(path)])
        except Exception as exc:
            messagebox.showerror(self.t('error_title'), self._error_text(exc), parent=self)

    def _open_folder(self):
        self.folder = self.settings.folder(self.root_dir)
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            self._open_path(self.folder)
        except OSError as exc:
            messagebox.showerror(self.t('folder_title'), str(exc), parent=self)

    def _hide(self):
        if self.settings_window and self.settings_window.winfo_exists():self._close_settings()
        self.hidden = True
        if self.tray.start():
            self.withdraw()
        else:
            self.iconify()

    def _restore(self):
        self.hidden = False
        self.deiconify()
        self.lift()
        self.focus_force()

    def _settings(self, page='profile'):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_notebook.select(self.setting_pages[page])
            self.settings_window.lift()
            self._refresh_history()
            return
        window = self.settings_window = tk.Toplevel(self)
        window.title(self.t('settings'))
        window.geometry('880x660')
        window.minsize(830, 620)
        window.configure(bg=BG)
        window.protocol('WM_DELETE_WINDOW', self._close_settings)
        footer=tk.Frame(window,bg=BG)
        footer.pack(side='bottom',fill='x',padx=22,pady=16)
        self._button(footer,'save',self._save_settings).pack(side='right')
        self._button(footer,'close_settings',self._close_settings,True).pack(side='right',padx=10)
        container=tk.Frame(window,bg=BG);container.pack(fill='both',expand=True,padx=18,pady=(18,0))
        sidebar=tk.Frame(container,bg=BG,width=160);sidebar.pack(side='left',fill='y',padx=(0,18));sidebar.pack_propagate(False)
        tk.Label(sidebar,text='DLPapp',font=(FONT,18,'bold'),bg=BG,fg=FG).pack(anchor='w',pady=(4,4))
        tk.Label(sidebar,text=VERSION,font=(FONT,10),bg=BG,fg=MUTED).pack(anchor='w',pady=(0,24))
        self.navigation={}
        def select(selected):
            for frame,button in self.navigation.items():
                button.configure(bg='#173b35' if frame==selected else BG,fg=GREEN if frame==selected else MUTED)
        notebook=self.settings_notebook=PageStack(container,on_select=select)
        notebook.pack(side='right',fill='both',expand=True)
        self.setting_pages={}
        for key in ('profile','general','downloads','updates','about'):
            frame=tk.Frame(notebook,bg=BG,padx=12,pady=8)
            notebook.add(frame,text=self.t(key));self.setting_pages[key]=frame
            button=tk.Button(sidebar,text=self.t(key),command=lambda f=frame:notebook.select(f),
                             bg=BG,fg=MUTED,relief='flat',highlightthickness=0,anchor='w',padx=14,pady=13,font=(FONT,11),cursor='hand2')
            button.pack(fill='x',pady=3);self.navigation[frame]=button
            self._label(frame,key,fg=FG,font=(FONT,19,'bold')).pack(anchor='w',pady=(0,20))
        profile = self.setting_pages['profile']
        self._label(profile, 'nickname', fg=MUTED).pack(anchor='w')
        self.nickname_choice = tk.StringVar(value=self.settings.get('nickname'))
        self._entry(profile, self.nickname_choice).pack(fill='x', ipady=12, pady=12)
        self._label(profile, 'privacy', fg=MUTED, wraplength=580, justify='left').pack(anchor='w', pady=12)
        general = self.setting_pages['general']
        self._label(general, 'language', fg=MUTED).pack(anchor='w')
        self.language_selector = ttk.Combobox(general, values=[self.t('auto'), 'English', 'Русский'], state='readonly')
        self.language_selector.pack(fill='x', pady=12)
        self.language_selector.current(['auto', 'en', 'ru'].index(self.settings.get('language')))
        self._label(general, 'download_parent', fg=MUTED).pack(anchor='w', pady=(20, 0))
        self.parent_choice = tk.StringVar(value=self.settings.get('download_parent'))
        row = tk.Frame(general, bg=BG)
        row.pack(fill='x', pady=12)
        self._entry(row, self.parent_choice).pack(side='left', fill='x', expand=True, ipady=10)
        self._button(row, 'browse', self._browse_folder, True).pack(side='right', padx=(8, 0))
        self._button(general, 'reset_folder', lambda: self.parent_choice.set(''), True).pack(anchor='w')
        self._label(general, 'folder_note', fg=MUTED, wraplength=580, justify='left').pack(anchor='w', pady=16)
        downloads = self.setting_pages['downloads']
        self.history_folder = tk.Label(downloads, bg=BG, fg=MUTED, wraplength=580, justify='left', anchor='w')
        self.history_folder.pack(fill='x', pady=(0, 8))
        table = tk.Frame(downloads, bg=CARD)
        table.pack(fill='both', expand=True)
        self.history_tree = ttk.Treeview(table, columns=('title', 'format', 'date'), show='headings', selectmode='browse',height=5)
        for key, width in [('title', 300), ('format', 90), ('date', 150)]:
            self.history_tree.heading(key, text=self.t('history_' + key))
            self.history_tree.column(key, width=width, minwidth=50, stretch=key == 'title')
        scrollbar = ttk.Scrollbar(table, command=self.history_tree.yview)
        self.history_tree.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.history_tree.pack(fill='both', expand=True)
        self.history_empty=tk.Label(table,text=self.t('history_empty'),bg=CARD,fg=MUTED,font=(FONT,11),wraplength=400)
        self.history_tree.bind('<Double-1>', lambda _e: self._history_open())
        actions = tk.Frame(downloads, bg=BG)
        actions.pack(fill='x', pady=10)
        self._button(actions, 'open_file', self._history_open, True).pack(side='left')
        self._button(actions, 'open_folder', self._open_folder, True).pack(side='left', padx=8)
        self._button(downloads, 'clear_history', self._clear_history, True).pack(anchor='w')
        page_updates = self.setting_pages['updates']
        self.auto_app_choice = tk.BooleanVar(value=self.settings.get('auto_updates'))
        self.auto_ytdlp_choice = tk.BooleanVar(value=self.settings.get('auto_ytdlp'))
        for key, variable in [('auto_updates', self.auto_app_choice), ('auto_ytdlp', self.auto_ytdlp_choice)]:
            tk.Checkbutton(page_updates, text=self.t(key), variable=variable, bg=BG, fg=FG, activebackground=BG,
                           activeforeground=FG, selectcolor=CARD,highlightthickness=0,bd=0,
                           font=(FONT, 10)).pack(anchor='w', pady=5)
        self._label(page_updates, 'update_schedule', fg=MUTED, wraplength=580, justify='left', font=(FONT, 9)).pack(anchor='w', pady=10)
        self._button(page_updates, 'check_updates', lambda: self._maintenance(app=True, manual=True), True).pack(anchor='w', pady=6)
        self._button(page_updates, 'update_ytdlp', lambda: self._maintenance(ytdlp=True, manual=True), True).pack(anchor='w', pady=6)
        tk.Label(page_updates, text=self.t('current_version', version=VERSION), bg=BG, fg=MUTED).pack(anchor='w', pady=8)
        tk.Label(page_updates, textvariable=self.update_status, bg=BG, fg=GREEN, wraplength=580, justify='left').pack(anchor='w')
        self.install_button = self._button(page_updates, 'install_update', self._install_update)
        self.install_button.pack(anchor='w', pady=10)
        self.install_button.config(state='normal' if self.pending_release else 'disabled')
        self._button(page_updates, 'release_page', lambda: webbrowser.open(GITHUB_URL + '/releases/latest'), True).pack(anchor='w')
        about = self.setting_pages['about']
        tk.Label(about, text='DLPapp ' + VERSION, bg=BG, fg=FG, font=(FONT, 23, 'bold')).pack(anchor='w')
        self._label(about, 'about_text', fg=MUTED, wraplength=580, justify='left').pack(anchor='w', pady=20)
        tk.Label(about, text=self.t('author', name=AUTHOR), bg=BG, fg=FG).pack(anchor='w', pady=8)
        tk.Button(about, text=GITHUB_URL, command=lambda: webbrowser.open(GITHUB_URL), bg=BG, fg=GREEN,
                  relief='flat', highlightthickness=0, cursor='hand2').pack(anchor='w')
        notebook.select(self.setting_pages[page])
        self._refresh_history()

    def _close_settings(self):
        self.settings_window.destroy()
        self.settings_window, self.history_tree = None, None
        self.text_widgets = [(w, k) for w, k in self.text_widgets if w.winfo_exists()]

    def _browse_folder(self):
        value = filedialog.askdirectory(parent=self.settings_window, initialdir=self.parent_choice.get() or str(self.root_dir))
        if value:
            self.parent_choice.set(value)

    def _save_settings(self):
        try:
            parent = self.parent_choice.get().strip()
            if parent:
                parent = str(Path(parent).expanduser().resolve())
            choice = ['auto', 'en', 'ru'][self.language_selector.current()]
            self.settings.update(nickname=self.nickname_choice.get().strip()[:40], language=choice,
                                 download_parent=parent, auto_updates=self.auto_app_choice.get(),
                                 auto_ytdlp=self.auto_ytdlp_choice.get())
        except (OSError, ValueError) as exc:
            messagebox.showerror(self.t('error_title'), self.t('settings_error') + '\n' + str(exc), parent=self.settings_window)
            return
        old_language = self.language
        self.language = detect_language() if choice == 'auto' else choice
        self.folder = self.settings.folder(self.root_dir)
        self.nickname_label.config(text=self.settings.get('nickname') or self.t('subtitle'))
        if self.language != old_language:
            self.title(self.t('window'))
            for widget, key in self.text_widgets:
                if widget.winfo_exists():
                    widget.config(text=self.t(key))
            self.status.set(self.t(self._status_key, **self._status_values))
            if not self.info:
                self.title_text.set(self.t('no_video'))
                self.meta.set(self.t('quality_hint'))
            elif self.format.get() in AUDIO_FORMATS:
                self.quality.set(self.t('audio_only'))
            self.update_status.set(self.t('new_version', version=self.pending_release.version) if self.pending_release else '')
            self._close_settings()
            self._settings('general')
            self._options_changed()
        else:
            self._refresh_history()
        if not self.busy and not self.updating and not self.maintenance:
            self.set_status('settings_saved')

    def _refresh_history(self):
        if not self.history_tree or not self.history_tree.winfo_exists():
            return
        folder = self.settings.folder(self.root_dir)
        rows = self.settings.history(folder)
        self.history_folder.config(text=self.t('folder_now', folder=folder))
        if rows:self.history_empty.place_forget()
        else:self.history_empty.place(relx=.5,rely=.5,anchor='center')
        self.history_tree.delete(*self.history_tree.get_children())
        self.history_rows = {}
        for i, item in enumerate(rows):
            identifier = str(i)
            self.history_rows[identifier] = item
            self.history_tree.insert('', 'end', iid=identifier, values=(item['title'] or Path(item['path']).name,
                                      item.get('format', ''), item.get('date', '')[:16].replace('T', ' ')))

    def _history_open(self):
        selection = self.history_tree.selection() if self.history_tree else []
        if selection:
            self._open_path(self.history_rows[selection[0]]['path'])

    def _clear_history(self):
        if not messagebox.askyesno(self.t('downloads'), self.t('clear_question'), parent=self.settings_window):
            return
        folder = os.path.normcase(str(self.settings.folder(self.root_dir).resolve()))
        try:
            self.settings.update(history=[x for x in self.settings.get('history') if os.path.normcase(x['folder']) != folder])
            self._refresh_history()
        except OSError:
            messagebox.showerror(self.t('error_title'), self.t('settings_error'), parent=self.settings_window)

    def _auto_updates(self):
        if not self.busy and not self.maintenance and not self.updating:
            self._maintenance(app=self.settings.get('auto_updates') and updates.due(self.settings.get('last_app_check')),
                              ytdlp=self.settings.get('auto_ytdlp') and updates.due(self.settings.get('last_ytdlp_check')))
        self.after(5 * 60 * 1000, self._auto_updates)

    def _maintenance(self, app=False, ytdlp=False, manual=False):
        if not app and not ytdlp:
            return
        if self.busy or self.maintenance or self.updating:
            if manual:
                messagebox.showinfo('DLPapp', self.t('wait_operation'), parent=self.settings_window or self)
            return
        ytdlp = ytdlp and os.name == 'nt'
        if not app and not ytdlp:
            self.update_status.set(self.t('windows_only'))
            return
        self.maintenance = True
        self._set_busy(False)
        self.update_status.set(self.t('update_checking' if app else 'ytdlp_updating'))
        def worker():
            for enabled, name, function, stamp in [(app, 'update', updates.check_app, 'last_app_check'),
                                                   (ytdlp, 'ytdlp', updates.update_ytdlp, 'last_ytdlp_check')]:
                if enabled:
                    try:
                        self.events.put((name + '_result', function()))
                    except Exception as exc:
                        self.events.put((name + '_error', exc))
                    finally:
                        try:
                            self.settings.update(**{stamp: time.time()})
                        except OSError as exc:
                            self.events.put((name + '_error', exc))
            self.events.put(('update_idle', None))
        threading.Thread(target=worker, daemon=True).start()

    def _update_event(self, kind, data):
        if kind == 'update_idle':
            self.maintenance = False
            self._set_busy(self.busy)
        elif kind == 'update_result':
            self.pending_release = data
            text = self.t('new_version', version=data.version) if data else self.t('latest')
            self.update_status.set(text)
            if data:
                self.set_status('new_version', version=data.version)
                self.tray.notify('DLPapp', text)
            if self.settings_window and self.settings_window.winfo_exists():
                self.install_button.config(state='normal' if data else 'disabled')
        elif kind == 'ytdlp_result':
            if not self.pending_release:
                self.update_status.set(self.t('ytdlp_done', version=data))
        elif kind in ('update_error', 'ytdlp_error'):
            self.update_status.set(self.t('update_failed', error=self._error_text(data)))
        elif kind == 'update_progress':
            self.update_status.set(self.t('update_progress', percent=f'{data[0]:.1f}', speed=data[1] / 1024**2))
            if getattr(self, 'update_bar', None) and self.update_bar.winfo_exists():
                self.update_bar['value'] = data[0]
        elif kind == 'update_download_error':
            self.updating = False
            self._set_busy(False)
            self.update_status.set(self.t('update_failed', error=self._error_text(data)))
            if self.update_window.winfo_exists():
                self.update_window.destroy()
            messagebox.showerror(self.t('updates'), self._error_text(data), parent=self)
        elif kind == 'update_download_done':
            try:
                updates.schedule_install(data, self.update_target, self.pending_release.digest, self.pending_release.version)
                self._quit()
            except Exception as exc:
                self._update_event('update_download_error', exc)

    def _install_update(self):
        if not self.pending_release:
            return
        if self.busy or self.maintenance or self.updating:
            messagebox.showinfo('DLPapp', self.t('wait_operation'), parent=self.settings_window or self)
            return
        target = updates.executable_path()
        if os.name != 'nt' or not target:
            webbrowser.open(self.pending_release.url)
            return
        if not messagebox.askyesno(self.t('updates'), self.t('update_question'), parent=self.settings_window or self):
            return
        self.update_target, self.updating = target, True
        self.update_cancel.clear()
        self._set_busy(False)
        win = self.update_window = tk.Toplevel(self)
        win.title(self.t('updates'))
        win.geometry('460x150')
        win.configure(bg=BG)
        tk.Label(win, textvariable=self.update_status, bg=BG, fg=FG, wraplength=430).pack(pady=16)
        self.update_bar = ttk.Progressbar(win, maximum=100)
        self.update_bar.pack(fill='x', padx=20)
        self._button(win, 'cancel', self.update_cancel.set, True).pack(pady=10)
        win.protocol('WM_DELETE_WINDOW', self.update_cancel.set)
        release = self.pending_release
        def worker():
            try:
                path = self.settings.path.parent / 'updates' / ('DLPapp-' + release.version + '.exe')
                updates.download_asset(release, path, lambda p, s: self.events.put(('update_progress', (p, s))), self.update_cancel)
                if self.update_cancel.is_set():
                    raise AppError('update_cancelled')
                self.events.put(('update_download_done', path))
            except Exception as exc:
                self.events.put(('update_download_error', exc))
        threading.Thread(target=worker, daemon=True).start()

    def _acknowledge_update(self):
        value = os.environ.pop('DLPAPP_UPDATE_ACK', None)
        if value:
            try:
                path = Path(value).resolve()
                if path.parent == (self.settings.path.parent / 'updates').resolve() and path.name.endswith('.ready.json'):
                    atomic_json(path, dict(app_id='DLPapp', version=VERSION, pid=os.getpid()))
            except OSError:
                pass

    def _quit(self):
        self.tray.close()
        self.destroy()

    def _close(self):
        if self.updating:
            self.update_window.lift()
            return
        if self.busy and self.kind == 'download':
            result = messagebox.askyesnocancel(self.t('close_title'), self.t('hide_question'), parent=self)
            if result is None:
                return
            if result:
                self._hide()
                return
            self._stop()
            self.after(100, self._close_when_stopped)
        elif self.busy:
            if messagebox.askyesno(self.t('close_title'), self.t('close_question'), parent=self):
                self._stop()
                self.after(100, self._close_when_stopped)
        elif self.maintenance:
            self.after(150, self._close_when_maintenance_done)
        else:
            self._quit()

    def _close_when_maintenance_done(self):
        if self.maintenance:
            self.after(150, self._close_when_maintenance_done)
        else:
            self._quit()

    def _close_when_stopped(self):
        if self.busy:
            self.after(100, self._close_when_stopped)
        else:
            self._quit()


if __name__ == '__main__':
    DLPapp().mainloop()
