import tkinter as tk
import tkinter.ttk as ttk
import pathlib

from dialogue_boxes.ttkDialogue import TtkDialog


class TextPopup(TtkDialog):
    def __init__(self, master, text_file, title):
        self.text_file = text_file
        super().__init__(master, title=title)

    def body(self, master):
        ttk.Label(master, text='UCI MOSS GUI').pack(side='top')
        text = tk.Text(master, width=73, height=36,
                       font=self.master.master.style.lookup(self.master.master.style, 'font'))
        scrollbar = ttk.Scrollbar(master)
        scrollbar.config(command=text.yview)
        text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        with open(pathlib.Path('resources').joinpath(self.text_file), 'r') as about:
            text.insert(tk.INSERT, about.read())
        text.config(state=tk.DISABLED)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def buttonbox(self):
        """add button box."""
        backdrop = ttk.Frame(self)
        bbox = ttk.Frame(backdrop)
        backdrop.pack(expand=1, fill=tk.BOTH)
        bbox.pack()
        w = ttk.Button(bbox, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
