import tkinter as tk
import tkinter.ttk as ttk
import pathlib
from tkinter import filedialog, messagebox

from dialogue_boxes.ttkDialogue import TtkDialog


def popup_builder(name_filter_label: str, file_dialogue_function, selection_type: str, title: str):
    class Popup(TtkDialog):
        def __init__(self, parent):
            super().__init__(parent, title=title)

        def body(self, master):
            window = ttk.Frame(master)
            window.pack(expand=1, fill='both')

            self.file = tk.StringVar(self)
            ttk.Label(window, text='Select File' if file_dialogue_function is not None else 'Path: ').grid(column=0,
                                                                                                           row=0)
            ttk.Entry(window, textvariable=self.file).grid(column=1, row=0)

            self.name = tk.StringVar(self)
            if selection_type == 'wildcard':
                self.name.set('(.*)')
            ttk.Label(window, text=name_filter_label).grid(column=0, row=1)
            ttk.Entry(window, textvariable=self.name).grid(column=1, row=1)

            self.unzip_name = tk.StringVar(self)
            if selection_type == 'directory_of_zip':
                ttk.Label(window, text='Name of File(s) in zipfile to submit, separated by a ";"').grid(column=0, row=2)
                ttk.Entry(window, textvariable=self.unzip_name).grid(column=1, row=2)
                self.dir_name = tk.BooleanVar(self, False)
                ttk.Checkbutton(window, text='Use Directory mode naming convention', variable=self.dir_name).grid(
                    column=2, row=1)

            self.submission_type = tk.StringVar(self)
            self.submission_type.set('Base Files')
            ttk.Label(window, text='Submission Type').grid(column=0, row=3)
            ttk.OptionMenu(window, self.submission_type, self.submission_type.get(),
                           *['Base Files', 'Current Student Submissions', 'Past Student Submissions']).grid(column=1,
                                                                                                            row=3)
            if selection_type == 'checkmate':
                ttk.Label(window, text='Enable directory mode for best results').grid(row=4, column=1)

            if file_dialogue_function is not None:
                def _browse_files():
                    selected_file = file_dialogue_function()
                    if selected_file:
                        self.file.set(selected_file)
                        if not self.name.get():
                            if file_dialogue_function == filedialog.askopenfilename:
                                self.name.set(pathlib.Path(selected_file).name)
                            else:
                                if selection_type != 'checkmate':
                                    self.name.set('(.*)')

                ttk.Button(window, text='Browse...', command=_browse_files).grid(column=2, row=0)

        def validate(self):
            try:
                # TODO: Check to see if file already exists in system
                path, name, sub_type = self.file.get(), self.name.get(), self.submission_type.get()
                assert path != ''
                if selection_type == 'directory_of_zip':
                    filename = self.unzip_name.get()
                    dir_mode = self.dir_name.get()
                    self.result = path, name, sub_type, selection_type, filename, dir_mode
                else:
                    self.result = path, name, sub_type, selection_type
                return True
            except AssertionError:
                messagebox.showwarning(
                    "Selected Error",
                    "Please make a valid selection or hit cancel.\n"
                    # "A file of the same name already exists, please select a different one, or hit cancel."
                )
                return False

        def apply(self):
            self.master.update_tree(*self.result)

    return Popup
