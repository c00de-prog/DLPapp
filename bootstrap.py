"""Entry point for a cached portable Python runtime."""
import ctypes
import os
import sys
from pathlib import Path


def main():
    runtime = Path(__file__).resolve().parent
    sys._MEIPASS = str(runtime)
    sys.dlpapp_home = Path(os.environ.get('DLPAPP_HOME', str(runtime)))
    os.environ['TCL_LIBRARY'] = str(runtime / 'tcl' / 'tcl8.6')
    os.environ['TK_LIBRARY'] = str(runtime / 'tcl' / 'tk8.6')
    from app import DLPapp
    DLPapp().mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        ctypes.windll.user32.MessageBoxW(None, traceback.format_exc(), 'DLPapp: startup error', 0x10)
        sys.exit(1)
