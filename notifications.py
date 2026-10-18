"""Lazy Win32 tray icon and balloon notification; no extra GUI dependencies."""
import os
import queue
import threading
import time
from pathlib import Path


class DeliveryWatch:
    """A successful Shell call is not proof that a notification was shown."""
    def __init__(self, events, clock=time.monotonic, timeout=5):
        self.events, self.clock, self.timeout = events, clock, timeout
        self.pending = None
        self.deadline = 0

    def begin(self, tag):
        self.failed('Replaced by another notification')
        self.pending = tag
        self.deadline = self.clock() + self.timeout

    def shown(self):
        if self.pending is not None:
            self.events.put(('notification_shown', self.pending))
            self.pending = None

    def failed(self, reason):
        if self.pending is not None:
            self.events.put(('notification_failed', (self.pending, reason)))
            self.pending = None

    def expire(self):
        if self.pending is not None and self.clock() >= self.deadline:
            self.failed('Windows did not confirm notification display')


class Tray:
    def __init__(self, events, icon_path, log_path=None):
        self.events, self.icon_path = events, str(icon_path)
        self.commands = queue.Queue()
        self.started = threading.Event()
        self.available = False
        self.hwnd = None
        self.thread = None
        self.closed = threading.Event()
        self.log_path = Path(log_path) if log_path else None
        self.delivery = DeliveryWatch(events)

    def start(self):
        if self.closed.is_set() or os.name != 'nt':
            return False
        if self.thread is None:
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
        self.started.wait(1)
        return self.available

    def notify(self, title, text, tag=None):
        if not self.start():
            self.log('Tray not available; GUI fallback required')
            return False
        self.commands.put((title[:63], text[:255], tag))
        return True

    def log(self, message):
        if not self.log_path:
            return
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            if self.log_path.exists() and self.log_path.stat().st_size > 128 * 1024:
                self.log_path.write_text('', encoding='utf-8')
            with self.log_path.open('a', encoding='utf-8') as stream:
                stream.write(time.strftime('%Y-%m-%d %H:%M:%S ') + message + '\n')
        except OSError:
            pass

    def close(self):
        self.closed.set()
        self.commands.put(None)

    def _run(self):
        try:
            self._run_windows()
        except Exception as exc:
            self.log('Tray initialization failed: ' + repr(exc))
            self.available = False
            self.delivery.failed('Tray initialization failed')
            self.events.put(('tray_failed', None))
        finally:
            self.started.set()

    def _run_windows(self):
        import ctypes as c
        from ctypes import wintypes as w
        user, shell, kernel = c.WinDLL('user32', use_last_error=True), c.WinDLL('shell32', use_last_error=True), c.WinDLL('kernel32')
        LRESULT = c.c_ssize_t
        WNDPROC = c.WINFUNCTYPE(LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        class WNDCLASS(c.Structure):
            _fields_ = [('style', w.UINT), ('lpfnWndProc', WNDPROC), ('cbClsExtra', c.c_int),
                        ('cbWndExtra', c.c_int), ('hInstance', w.HINSTANCE), ('hIcon', w.HICON),
                        ('hCursor', w.HANDLE), ('hbrBackground', w.HBRUSH), ('lpszMenuName', w.LPCWSTR),
                        ('lpszClassName', w.LPCWSTR)]
        class GUID(c.Structure):
            _fields_ = [('a', w.DWORD), ('b', w.WORD), ('c', w.WORD), ('d', c.c_byte * 8)]
        class NID(c.Structure):
            _fields_ = [('cbSize', w.DWORD), ('hWnd', w.HWND), ('uID', w.UINT), ('uFlags', w.UINT),
                        ('uCallbackMessage', w.UINT), ('hIcon', w.HICON), ('szTip', w.WCHAR * 128),
                        ('dwState', w.DWORD), ('dwStateMask', w.DWORD), ('szInfo', w.WCHAR * 256),
                        ('uTimeout', w.UINT), ('szInfoTitle', w.WCHAR * 64), ('dwInfoFlags', w.DWORD),
                        ('guidItem', GUID), ('hBalloonIcon', w.HICON)]
        user.DefWindowProcW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        user.DefWindowProcW.restype = LRESULT
        user.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, c.c_int, c.c_int,
                                        c.c_int, c.c_int, w.HWND, w.HMENU, w.HINSTANCE, c.c_void_p]
        user.CreateWindowExW.restype = w.HWND
        kernel.GetModuleHandleW.argtypes = [w.LPCWSTR]
        kernel.GetModuleHandleW.restype = w.HINSTANCE
        user.LoadImageW.argtypes = [w.HINSTANCE, w.LPCWSTR, w.UINT, c.c_int, c.c_int, w.UINT]
        user.LoadImageW.restype = w.HANDLE
        user.DestroyIcon.argtypes = [w.HICON]
        user.DestroyWindow.argtypes = [w.HWND]
        user.RegisterClassW.argtypes = [c.POINTER(WNDCLASS)]
        user.UnregisterClassW.argtypes = [w.LPCWSTR, w.HINSTANCE]
        shell.Shell_NotifyIconW.argtypes = [w.DWORD, c.POINTER(NID)]
        shell.Shell_NotifyIconW.restype = w.BOOL
        user.PeekMessageW.argtypes = [c.POINTER(w.MSG), w.HWND, w.UINT, w.UINT, w.UINT]
        user.PeekMessageW.restype = w.BOOL
        user.TranslateMessage.argtypes = [c.POINTER(w.MSG)]
        user.TranslateMessage.restype = w.BOOL
        user.DispatchMessageW.argtypes = [c.POINTER(w.MSG)]
        user.DispatchMessageW.restype = LRESULT
        user.RegisterClassW.restype = w.WORD
        user.UnregisterClassW.restype = w.BOOL
        user.DestroyWindow.restype = w.BOOL
        user.LoadIconW.argtypes = [w.HINSTANCE, w.LPCWSTR]
        user.LoadIconW.restype = w.HICON
        user.RegisterWindowMessageW.argtypes = [w.LPCWSTR]
        user.RegisterWindowMessageW.restype = w.UINT
        taskbar_created = user.RegisterWindowMessageW('TaskbarCreated')
        callback_message = 0x8001
        data = None
        @WNDPROC
        def callback(hwnd, message, wp, lp):
            if message == taskbar_created and data is not None:
                data.uFlags = 7
                self.available = bool(shell.Shell_NotifyIconW(0, c.byref(data)))
                if not self.available:
                    self.events.put(('tray_failed', None))
                return 0
            if message == callback_message:
                event = int(lp) & 0xffff
                if event == 0x402:  # NIN_BALLOONSHOW
                    self.delivery.shown()
                    self.log('Windows confirmed notification display')
                elif event in (0x403, 0x404):  # hidden before showing / timed out
                    self.delivery.failed('Notification hidden or dismissed before display confirmation')
                elif event in (0x202, 0x205, 0x405, 0x400, 0x401):
                    if event == 0x405:
                        self.delivery.shown()
                    self.events.put(('restore', None))
                return 0
            return user.DefWindowProcW(hwnd, message, wp, lp)
        instance = kernel.GetModuleHandleW(None)
        name = 'DLPappTray-' + str(os.getpid())
        window_class = WNDCLASS()
        window_class.lpfnWndProc, window_class.hInstance, window_class.lpszClassName = callback, instance, name
        icon = None
        owned_icon = False
        try:
            if not user.RegisterClassW(c.byref(window_class)):
                return
            self.hwnd = user.CreateWindowExW(0, name, 'DLPapp', 0, 0, 0, 0, 0, None, None, instance, None)
            if not self.hwnd:
                return
            icon = user.LoadImageW(None, self.icon_path, 1, 16, 16, 0x10)
            owned_icon = bool(icon)
            if not icon:
                icon = user.LoadIconW(None, c.cast(c.c_void_p(32512), w.LPCWSTR))
            if not icon:
                raise OSError('No tray icon available')
            data = NID()
            data.cbSize, data.hWnd, data.uID = c.sizeof(NID), self.hwnd, 1
            data.uFlags, data.uCallbackMessage, data.hIcon, data.szTip = 7, callback_message, icon, 'DLPapp — click to open'
            self.available = bool(shell.Shell_NotifyIconW(0, c.byref(data)))
            self.started.set()
            if not self.available:
                return
            message = w.MSG()
            while not self.closed.is_set():
                while user.PeekMessageW(c.byref(message), None, 0, 0, 1):
                    user.TranslateMessage(c.byref(message))
                    user.DispatchMessageW(c.byref(message))
                try:
                    command = self.commands.get(timeout=.08)
                    if command is None:
                        break
                    self.delivery.begin(command[2])
                    data.uFlags = 0x10
                    data.szInfoTitle, data.szInfo, data.dwInfoFlags, data.uTimeout = command[0], command[1], 0x81, 10000
                    if not shell.Shell_NotifyIconW(1, c.byref(data)):
                        self.log('Shell_NotifyIconW failed: ' + str(c.get_last_error()))
                        self.delivery.failed('Windows rejected the notification')
                except queue.Empty:
                    pass
                self.delivery.expire()
        except Exception as exc:
            self.log('Tray error: ' + repr(exc))
            self.available = False
        finally:
            self.delivery.failed('Tray closed before display confirmation')
            if not self.closed.is_set():
                self.events.put(('tray_failed', None))
            self.started.set()
            if self.hwnd and data is not None:
                try:
                    shell.Shell_NotifyIconW(2, c.byref(data))
                    user.DestroyWindow(self.hwnd)
                except Exception:
                    pass
            if icon and owned_icon:
                user.DestroyIcon(icon)
            user.UnregisterClassW(name, instance)
            self.available = False
