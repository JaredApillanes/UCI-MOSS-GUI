import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
from dialogue_boxes.ttkDialogue import TtkDialog


class EditSettingsPopup(TtkDialog):
    def __init__(self, parent):
        super().__init__(parent, title='Edit Settings')

    def body(self, master):
        # TODO: Add other settings.
        window = ttk.Frame(master)
        window.pack(expand=1, fill='both')
        ttk.Label(master, text='Network Threshold').pack(side='top')
        vcmd = (self.register(self._validate_spin), '%S')
        ttk.Entry(master, textvariable=self.master.master.master.master.tab_settings.network_threshold,
                  validatecommand=vcmd, validate='key').pack()

    def validate(self):
        try:
            assert self.master.master.master.master.tab_settings.network_threshold.get() is not None
            assert 0 <= self.master.master.master.master.tab_settings.network_threshold.get() < 100
            return True
        except AssertionError:
            messagebox.showwarning(
                "Network Threshold Error",
                f"Invalid Percentage Threshold: must be an integer from 0 to 100 (inclusive)."
            )
            return False
        except tk.TclError:
            messagebox.showwarning(
                "Network Threshold Error",
                "Invalid Percentage Threshold: must be an integer from 0 to 100 (inclusive)."
            )
            return False

    def _validate_spin(self, single_change):
        if single_change.isdigit():
            return True
        else:
            self.bell()
            return False

    def apply(self):
        return self.result
