"""Layout-independent Windows shortcuts plus a localized context menu."""
import os
import tkinter as tk


def paste(widget):
    try:
        text = widget.clipboard_get()
    except tk.TclError:
        return 'break'
    if str(widget.cget('state')) == 'disabled':
        return 'break'
    try:
        widget.delete('sel.first', 'sel.last')
    except tk.TclError:
        pass
    widget.insert('insert', text)
    return 'break'


def select_all(widget):
    widget.selection_range(0, 'end')
    widget.icursor('end')
    return 'break'


def bind_entry(widget, t):
    # Windows keycode is a virtual key independent of the RU/EN layout.
    def control(event):
        if not event.state & 4:
            return None
        key = {65: 'a', 67: 'c', 86: 'v', 88: 'x'}.get(event.keycode) if os.name == 'nt' else event.keysym.lower()
        if key == 'v':
            return paste(widget)
        if key == 'a':
            return select_all(widget)
        if key in ('c', 'x'):
            widget.event_generate('<<Copy>>' if key == 'c' else '<<Cut>>')
            return 'break'
    widget.bind('<Control-KeyPress>', control)
    widget.bind('<Shift-Insert>', lambda _e: paste(widget))
    menu = tk.Menu(widget, tearoff=False)
    def popup(event):
        menu.delete(0, 'end')
        for key, command in [('paste', lambda: paste(widget)), ('copy', lambda: widget.event_generate('<<Copy>>')),
                             ('cut', lambda: widget.event_generate('<<Cut>>')), ('select_all', lambda: select_all(widget))]:
            menu.add_command(label=t(key), command=command)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return 'break'
    widget.bind('<Button-3>', popup)
