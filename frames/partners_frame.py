import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
import inspect
from collections import defaultdict
import pathlib

try:
    from scripts.partner_converter import partner_formatter

    FAILED_IMPORT = False
except ImportError:
    print(
        'Error importing custom partner formatting script from scripts.partner_converter @ func: partner_formatter\n'
        'Loading default handler...')
    FAILED_IMPORT = True
    partner_formatter = (lambda path_to_csv: eval(open(path_to_csv).read()))


class TabPartners(ttk.Frame):
    def __init__(self, master, **kwargs):
        padding = 5
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=2)

        # File Selection
        file_selector_panel = ttk.Labelframe(self, text='Partners File:')
        file_selector_panel.grid(column=0, row=0, sticky='news', padx=padding, pady=padding)

        partners_file = tk.StringVar(self)
        ttk.Label(file_selector_panel, text='Select Partner File').pack(side='left')
        file_button = ttk.Entry(file_selector_panel, textvariable=partners_file)
        file_button.pack(side='left')

        def _browse_partners():
            selected_file = filedialog.askopenfilename()
            if selected_file:
                partners_file.set(selected_file)

        ttk.Button(file_selector_panel, text='Browse...', command=_browse_partners).pack()

        # Dynamic Script Parameter Fields
        dynamic_settings_panel = ttk.Labelframe(self, text='Custom Parameters:', padding=10)
        dynamic_settings_panel.grid(column=1, row=0, rowspan=2, sticky='news', padx=padding, pady=padding)
        if FAILED_IMPORT:
            ttk.Label(dynamic_settings_panel,
                      text='Error importing custom partner formatting script from\n'
                           '    scripts.partner_converter @func: partner_formatter\n'
                           'Loading default handler...\n'
                           'Default Handler assumes the file is formatted properly and needs no parsing.\n'
                           '    If necessary, edit the script and reload the program.\n'
                           '    See the HELP doc. in the info menu for more information.').pack()
        dynamic_kwargs = defaultdict((lambda: tk.StringVar(self)))
        dyn_entries = {}
        for arg in inspect.signature(partner_formatter).parameters:
            if arg == 'path_to_csv':
                continue
            ttk.Label(dynamic_settings_panel, text=arg.replace('_', ' ').title()).pack()
            dyn_entries[arg] = ttk.Entry(dynamic_settings_panel, textvariable=dynamic_kwargs[arg])
            dyn_entries[arg].pack()

        # Confirm Button and Validation
        def _validate_and_convert():
            if not (pathlib.Path(partners_file.get()).exists() and partners_file.get()):
                file_button.focus_force()
            else:
                for argument, var in dynamic_kwargs.items():
                    if not var.get():
                        dyn_entries[argument].focus_force()
                        break
                else:
                    dynamic_kwargs['path_to_csv'] = partners_file
                    try:
                        self.master.master.master.partners = partner_formatter(
                            **{argument: string_var.get() for argument, string_var in dynamic_kwargs.items()})
                    except BaseException as e:
                        messagebox.showerror(type(e),
                                             message=f"The parsing script at scripts.partner_converter raised the error"
                                                     f":\n{e}")
                    self._repopulate_tree()

        ttk.Button(dynamic_settings_panel, text='Convert Selected File', command=_validate_and_convert).pack()
        ttk.Button(dynamic_settings_panel, text='Clear All Partners', command=self._clear_partners).pack(pady=5)

        self.found_partners_panel = ttk.Treeview(self, column='#1')
        self.found_partners_panel.heading('#0', text='Student 1')
        self.found_partners_panel.heading('#1', text='Student 2')
        self.found_partners_panel.grid(column=0, row=1, sticky='news', padx=padding, pady=padding)

        # Display Found Partnerships

    def _repopulate_tree(self):
        for item in self.found_partners_panel.get_children():
            self.found_partners_panel.delete(item)
        for entry in self.master.master.master.partners:
            entry = list(entry)
            self.found_partners_panel.insert('', 'end', entry, text=entry[0], values=entry[1])

    def _clear_partners(self):
        if messagebox.askokcancel(title='Clear Partners', message='Are you sure you want to clear all partners?'):
            self.master.master.master.partners = {}
            self._repopulate_tree()
