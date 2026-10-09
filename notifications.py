"""Lazy Win32 tray icon and balloon notification; no extra GUI dependencies."""
import os
import queue
import threading


class Tray:
    def __init__(self, events, icon_path):
        self.events, self.icon_path = events, str(icon_path)
        self.commands = queue.Queue()
        self.started = threading.Event()
        self.available = False
        self.hwnd = None
        self.thread = None

    def start(self):
        if os.name != 'nt':
            return False
        if self.thread is None:
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
        self.started.wait(1)
        return self.available

    def notify(self, title, text):
        if self.start():
            self.commands.put((title[:63], text[:255]))

    def close(self):
        self.commands.put(None)

    def _run(self):
        import ctypes as c
        from ctypes import wintypes as w
        user, shell, kernel = c.WinDLL('user32', use_last_error=True), c.WinDLL('shell32'), c.WinDLL('kernel32')
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
        callback_message = 0x8001
        @WNDPROC
        def callback(hwnd, message, wp, lp):
            if message == callback_message and lp in (0x202, 0x205, 0x405):
                self.events.put(('restore', None))
                return 0
            return user.DefWindowProcW(hwnd, message, wp, lp)
        instance = kernel.GetModuleHandleW(None)
        name = 'DLPappTray-' + str(os.getpid())
        window_class = WNDCLASS()
        window_class.lpfnWndProc, window_class.hInstance, window_class.lpszClassName = callback, instance, name
        icon = None
        try:
            if not user.RegisterClassW(c.byref(window_class)):
                return
            self.hwnd = user.CreateWindowExW(0, name, 'DLPapp', 0, 0, 0, 0, 0, None, None, instance, None)
            if not self.hwnd:
                return
            icon = user.LoadImageW(None, self.icon_path, 1, 16, 16, 0x10)
            data = NID()
            data.cbSize, data.hWnd, data.uID = c.sizeof(NID), self.hwnd, 1
            data.uFlags, data.uCallbackMessage, data.hIcon, data.szTip = 7, callback_message, icon, 'DLPapp — click to open'
            self.available = bool(shell.Shell_NotifyIconW(0, c.byref(data)))
            self.started.set()
            if not self.available:
                return
            message = w.MSG()
            while True:
                while user.PeekMessageW(c.byref(message), None, 0, 0, 1):
                    user.TranslateMessage(c.byref(message))
                    user.DispatchMessageW(c.byref(message))
                try:
                    command = self.commands.get(timeout=.08)
                    if command is None:
                        break
                    data.uFlags = 0x10
                    data.szInfoTitle, data.szInfo, data.dwInfoFlags, data.uTimeout = command[0], command[1], 1, 10000
                    shell.Shell_NotifyIconW(1, c.byref(data))
                except queue.Empty:
                    pass
        except Exception:
            self.available = False
        finally:
            self.started.set()
            if self.hwnd:
                try:
                    shell.Shell_NotifyIconW(2, c.byref(data))
                    user.DestroyWindow(self.hwnd)
                except Exception:
                    pass
            if icon:
                user.DestroyIcon(icon)
            user.UnregisterClassW(name, instance)
            self.available = False
