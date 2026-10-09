"""Small native Tk drawing helpers; no third-party GUI packages."""
import tkinter as tk
from tkinter import font as tkfont


def rounded(canvas, x1, y1, x2, y2, radius, **options):
    r = min(radius, (x2-x1)/2, (y2-y1)/2)
    return canvas.create_polygon(x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,
        x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1,
        smooth=True, splinesteps=24, **options)


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, primary=False, font=('Segoe UI',10,'bold')):
        self.text, self.command, self.primary = text, command, primary
        self.text_font = tkfont.Font(font=font)
        self.hover = False
        super().__init__(parent, bg=parent.cget('bg'), width=self.text_font.measure(text)+34,
                         height=40, highlightthickness=0, bd=0, cursor='hand2', takefocus=True)
        self.bind('<Configure>', lambda _e:self.draw())
        self.bind('<Enter>', lambda _e:self._hover(True))
        self.bind('<Leave>', lambda _e:self._hover(False))
        self.bind('<Button-1>', lambda _e:self.focus_set())
        self.bind('<ButtonRelease-1>', lambda _e:self.invoke())
        self.bind('<space>', lambda _e:self.invoke())
        self.bind('<Return>', lambda _e:self.invoke())
        self.bind('<FocusIn>', lambda _e:self.draw())
        self.bind('<FocusOut>', lambda _e:self.draw())

    def _hover(self, value):
        self.hover = value
        self.draw()

    def invoke(self):
        if self.cget('state') != 'disabled':
            self.command()

    def configure(self, cnf=None, **options):
        if cnf is not None:
            return super().configure(cnf, **options)
        if 'text' in options:
            self.text = options.pop('text')
            options.setdefault('width',self.text_font.measure(self.text)+34)
        result = super().configure(**options)
        self.draw()
        return result
    config = configure

    def draw(self):
        if not self.winfo_exists():return
        self.delete('all')
        disabled = self.cget('state') == 'disabled'
        fill = '#1b2933' if disabled else ('#28ddb1' if self.hover else '#19c79c') if self.primary else ('#253742' if self.hover else '#1a2731')
        color = '#728390' if disabled else '#071b17' if self.primary else '#edf4f8'
        rounded(self,1,1,max(2,self.winfo_width()-1),39,10,fill=fill,outline='#384d59' if self.focus_get()==self else fill)
        self.create_text(self.winfo_width()/2,20,text=self.text,font=self.text_font,fill=color)


class Panel(tk.Canvas):
    def __init__(self, parent, color='#141f29', padding=18):
        self.color, self.padding = color,padding
        super().__init__(parent,bg=parent.cget('bg'),highlightthickness=0,bd=0,height=1)
        self.body=tk.Frame(self,bg=color)
        self.window=self.create_window(padding,padding,window=self.body,anchor='nw')
        self.bind('<Configure>',self._resize)
        self.body.bind('<Configure>',self._resize)

    def _resize(self,_event=None):
        width=max(1,self.winfo_width())
        self.itemconfigure(self.window,width=max(1,width-2*self.padding))
        height=self.body.winfo_reqheight()+2*self.padding
        if self.winfo_reqheight()!=height:self.configure(height=height)
        self.delete('surface')
        rounded(self,1,1,width-1,height-1,16,fill=self.color,outline='#22313d',tags='surface')
        self.tag_lower('surface')


class PageStack(tk.Frame):
    """Notebook-like API with flat sidebar navigation instead of native tabs."""
    def __init__(self,parent,on_select=None):
        super().__init__(parent,bg=parent.cget('bg'))
        self.on_select=on_select
        self.rowconfigure(0,weight=1);self.columnconfigure(0,weight=1)
        self.pages=[]
    def add(self,page,text=''):
        page.grid(row=0,column=0,sticky='nsew');self.pages.append(page)
    def select(self,page):
        page.tkraise()
        if self.on_select:self.on_select(page)
