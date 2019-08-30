import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont

import model
import pathlib
import json
from tkinter import filedialog
from tkinter import messagebox
import inspect
import re
import glob
import zipfile
from collections import defaultdict
from tempfile import TemporaryDirectory
import shutil

try:
    from scripts.partner_converter import partner_formatter
except ImportError:
    print(
        'Error importing custom partner formatting script from scripts.partner_converter @ func: partner_formatter\n'
        'Loading default handler...')
    partner_formatter = (lambda path_to_csv: eval(open(path_to_csv).read()))


class TtkDialog(tk.Toplevel):
    """Class to open dialogs.

    This class is intended as a base class for custom dialogs

    This class is a copy of the simpledialog.Dialog class,
    but implements the ttk protocol.
    """

    def __init__(self, parent, title=None):

        """Initialize a dialog.

        Arguments:

            parent -- a parent window (the application window)

            title -- the dialog title
        """
        tk.Toplevel.__init__(self, parent)

        self.withdraw()  # remain invisible for now
        # If the master is not viewable, don't
        # make the child transient, or else it
        # would be opened withdrawn
        if parent.winfo_viewable():
            self.transient(parent)

        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        body = ttk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(fill=tk.BOTH, expand=1)  # padx=5, pady=5

        self.buttonbox()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        if self.parent is not None:
            self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                      parent.winfo_rooty() + 50))

        self.deiconify()  # become visible now

        self.initial_focus.focus_set()

        # wait for window to appear on screen before calling grab_set
        self.wait_visibility()
        self.grab_set()
        self.wait_window(self)

    def destroy(self):
        """Destroy the window"""
        self.initial_focus = None
        tk.Toplevel.destroy(self)

    def body(self, master):
        """create dialog body.

        return widget that should have initial focus.
        This method should be overridden, and is called
        by the __init__ method.
        """
        pass

    def buttonbox(self):
        """add standard button box.

        override if you do not want the standard buttons
        """

        backdrop = ttk.Frame(self)
        bbox = ttk.Frame(backdrop)
        backdrop.pack(expand=1, fill=tk.BOTH)
        bbox.pack()
        w = ttk.Button(bbox, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = ttk.Button(bbox, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

    def ok(self, event=None):

        if not self.validate():
            self.initial_focus.focus_set()  # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        try:
            self.apply()
        finally:
            self.cancel()

    def cancel(self, event=None):

        # put focus back to the parent window
        if self.parent is not None:
            self.parent.focus_set()
        self.destroy()

    def validate(self):
        """validate the data

        This method is called automatically to validate the data before the
        dialog is destroyed. By default, it always validates OK.
        """

        return 1  # override

    def apply(self):
        """process the data

        This method is called automatically to process the data, *after*
        the dialog is destroyed. By default, it does nothing.
        """

        pass  # override


class WelcomePage(ttk.Frame):

    def __init__(self, master):
        super().__init__(master)
        welcome_title = ttk.Label(self, text="Welcome", font=('', 30))
        welcome_title.pack(pady=10, padx=10)

        introduction = ttk.Label(self, justify=tk.CENTER,
                                 text='A GUI for the command line tool "Moss" developed by Alex Aiken.'
                                      '\n\nAn Extension for the file selection and report filtration system.'
                                      '\n\nSee the About and Help pages in the Info menu for more information.'
                                      '\n\nNON-COMMERCIAL USE')
        introduction.pack()

        continue_button = ttk.Button(self, text="Continue", command=self._leave)
        continue_button.pack()

        self.disable_welcome_var = tk.BooleanVar(self, self.master.user_config['disable_welcome'])
        disable_welcome = ttk.Checkbutton(self, text='Do not show this page', variable=self.disable_welcome_var)
        disable_welcome.pack()

    def _leave(self):
        self.destroy()
        self.master.home.pack(expand=1, fill='both')


class UciMossGui(tk.Tk):
    def __init__(self, *args, **kwargs):
        self.temp_dir = None
        self.partners = {}
        self.user_config = {}
        self.load_saved_settings()
        self.moss = model.MossUCI(self.user_config['moss_id'], self.user_config['language'])

        super().__init__(*args, **kwargs)
        self.url_var = tk.StringVar(self)
        self.style = ttk.Style(self)
        self.style.theme_use(self.user_config['theme'])
        self.menus = MossMenu()
        self.config(menu=self.menus)

        self.title('University California, Irvine\'s MOSS system')
        self.home = ttk.Frame(self)
        self.welcome_page = WelcomePage(self)
        loaded_page = self.welcome_page if not self.user_config['disable_welcome'] else self.home
        loaded_page.pack(expand=1, fill='both')

        self.notebook = ttk.Notebook(self.home)

        self.tab_files = TabFiles(self.notebook)

        self.tab_partners = TabPartners(self.notebook)
        self.tab_settings = TabSettings(self.notebook)
        self.tab_submit = TabSubmit(self.notebook)
        self.notebook.add(self.tab_settings, text='Settings')
        self.notebook.add(self.tab_files, text='Files')
        self.notebook.add(self.tab_partners, text='Partners',
                          state=tk.NORMAL if self.user_config['filter'] else tk.DISABLED)
        self.notebook.add(self.tab_submit, text='Submission')
        self.notebook.pack(expand=1, fill='both')

    def load_saved_settings(self):
        try:
            with open('config.json', 'r') as open_io:
                config = json.load(open_io)
                assert all(
                    key in config.keys() for key in
                    ('moss_id', 'language', 'archive', 'filter', 'zip', 'network_threshold', 'disable_welcome',
                     'ignore_limit', 'review_before_archiving', 'download_report', 'directory_mode', 'theme'))
        except (OSError, ValueError, AssertionError):
            self.create_default_config()
            raise
        else:
            self.user_config = config

    def save_settings(self):
        config = {
            "moss_id": self.tab_settings.moss_id.get(),
            "language": self.tab_settings.language.get(),
            "archive": self.tab_settings.archive_locally.get(),
            "filter": self.tab_settings.filter_report.get(),
            "zip": self.tab_settings.zip_report.get(),
            "network_threshold": self.tab_settings.network_threshold.get(),
            "ignore_limit": self.tab_settings.ignore_limit.get(),
            "disable_welcome": self.welcome_page.disable_welcome_var.get(),
            "review_before_archiving": self.tab_submit.review_before.get(),
            "download_report": self.tab_settings.download_report.get(),
            "directory_mode": self.tab_settings.directory_mode_var.get(),
            "theme": self.style.theme_use()
        }
        with open('config.json', 'w') as config_file:
            json.dump(config, config_file)

    def create_default_config(self):
        # TODO: Doesn't affect at all
        self.user_config = {
            "moss_id": 563499553,
            "language": "python",
            "archive": False,
            "filter": False,
            "zip": False,
            "network_threshold": -1,
            "ignore_limit": 1000000,
            "disable_welcome": False,
            "review_before_archiving": False,
            "download_report": False,
            "directory_mode": False,
            "theme": "clam"
        }

    def run(self):
        with TemporaryDirectory(dir='.') as temp_dir:
            self.temp_dir = temp_dir
            self.geometry('800x533')
            self.mainloop()
            self.save_settings()

    def validate_and_send(self):
        self.tab_submit.stats_var.set('')
        self.notebook.tab(0, state=tk.DISABLED)
        self.notebook.tab(1, state=tk.DISABLED)
        self.notebook.tab(2, state=tk.DISABLED)
        self.tab_submit.unlock.config(state=tk.ACTIVE)
        self.tab_submit.submit.config(state=tk.DISABLED)
        self.tab_submit.progress_bar.start(10)
        self.after(1, self._validate_helper)

    def _validate_helper(self):
        config = {
            "moss_id": self.tab_settings.moss_id.get(),
            "language": self.tab_settings.language.get(),
            "archive": self.tab_settings.archive_locally.get(),
            "filter": self.tab_settings.filter_report.get(),
            "zip": self.tab_settings.zip_report.get(),
            "network_threshold": self.tab_settings.network_threshold.get(),
            "ignore_limit": self.tab_settings.ignore_limit.get(),
            "review_before_archiving": self.tab_submit.review_before.get(),
            "download_report": self.tab_settings.download_report.get(),
            "directory": self.tab_submit.dir_var.get(),
            "directory_mode": 1 if self.tab_settings.directory_mode_var.get() else 0
        }
        self.moss = model.MossUCI(config['moss_id'], config['language'])
        self.moss.debug = self.menus.debug_mode
        self.moss.setIgnoreLimit(config['ignore_limit'])
        self.moss.setDirectoryMode(config['directory_mode'])

        def sifter(item, add_function):
            if self.tab_files.file_display.get_children(item):
                for sub_item in self.tab_files.file_display.get_children(item):
                    sifter(sub_item, add_function)
            else:
                add_function(self.tab_files.file_display.item(item, "values")[0],
                             self.tab_files.file_display.item(item, "text").replace(' ', r'_'))

        for item in self.tab_files.file_display.get_children('I001'):
            sifter(item, self.moss.addBaseFile)
        for item in self.tab_files.file_display.get_children('I002'):
            sifter(item, self.moss.addFile)
        for item in self.tab_files.file_display.get_children('I003'):
            sifter(item, self.moss.add_old_students)

        try:
            url = self.moss.send()
        except ConnectionError:
            url = 'Error: Connection Disconnected by Host'
        # Is it a valid report?
        if url.startswith('Error') or not url:
            self.url_var.set('')
            self.tab_submit.stats_var.set(url)
            self.notebook.tab(0, state=tk.NORMAL)
            self.notebook.tab(1, state=tk.NORMAL)
            self.notebook.tab(2, state=tk.NORMAL if self.tab_settings.filter_report.get() else tk.DISABLED)
            self.tab_submit.archive_button.config()  # TODO: figure out what this was
            self.tab_submit.unlock.config(state=tk.DISABLED)
            self.tab_submit.submit.config(state=tk.ACTIVE)
            self.tab_submit.progress_bar.stop()
            messagebox.showerror('Connection Error',
                                 'Ensure you have a valid moss ID entered in the Settings Tab, and that you have added files to send.')
            return
        else:  # Valid Report
            self.url_var.set(url)
            if not config['review_before_archiving']:  # Handle now...
                if not config['download_report']:
                    config['directory'] = self.temp_dir
                self.moss.filter_report(path=config['directory'], partners=self.partners,
                                        archive=config['archive'],
                                        zip_report=config['zip'],
                                        network_threshold=config['network_threshold'], filter=config['filter'])
            else:  # else prime others to handle
                self.tab_submit.archive_button.config(state=tk.ACTIVE)
                if config['filter']:
                    self.tab_submit.edit_settings.config(state=tk.ACTIVE)
                self.moss.filter_report(self.temp_dir, self.partners, False, False, config['network_threshold'])
        self.tab_submit.update_tree()
        self.tab_submit.progress_bar.stop()

    def unlock_after_submit(self):
        self.notebook.tab(0, state=tk.NORMAL)
        self.notebook.tab(1, state=tk.NORMAL)
        self.notebook.tab(2, state=tk.NORMAL if self.tab_settings.filter_report.get() else tk.DISABLED)
        self.tab_submit.unlock.config(state=tk.DISABLED)
        self.tab_submit.submit.config(state=tk.ACTIVE)
        self.tab_submit.edit_settings.config(state=tk.DISABLED)
        self.tab_submit.archive_button.config(state=tk.DISABLED)


class MossMenu(tk.Menu):
    def __init__(self, master=None, cnf=None, **kw):
        if cnf is None:
            cnf = {}
        super().__init__(master, cnf, **kw)
        settings = tk.Menu(self)
        settings.add_command(label='Reset Preferences', command=self.master.create_default_config)
        self.debug_mode = tk.BooleanVar(self, False)
        settings.add_command(label='Show Welcome Page on Boot', command=self._reset_welcome_page)
        settings.add_separator()
        settings.add_checkbutton(label='Moss Terminal Debugger', variable=self.debug_mode)
        self.add_cascade(label='UI Settings', menu=settings)

        window = tk.Menu(self)

        themes = tk.Menu(self)
        self.theme_var = tk.StringVar(self, self.master.user_config['theme'])
        for theme in self.master.style.theme_names():
            themes.add_radiobutton(label=theme, variable=self.theme_var, command=self._change_theme(theme))
        window.add_cascade(label='Themes', menu=themes)
        window.add_separator()

        zoom = tk.Menu(self)
        self.zoom_var = tk.StringVar(self, '100%')
        for size in range(100, 201, 25):
            zoom.add_radiobutton(label=f"{size}%", variable=self.zoom_var, command=self._change_font(size))
        window.add_cascade(label='Font Size', menu=zoom)
        self.add_cascade(label='Window', menu=window)

        info_section = tk.Menu(self)
        info_section.add_command(label='About', command=(lambda: TextPopup(self, 'about_text.txt', 'About')))
        info_section.add_command(label='Help', command=(lambda: TextPopup(self, 'help_text.txt', 'Help')))
        self.add_cascade(label='Info', menu=info_section)

    def _reset_welcome_page(self):
        self.master.user_config['disable_welcome'] = False
        self.master.welcome_page.disable_welcome_var.set(False)

    def _change_theme(self, theme):
        def _built_func():
            self.master.style.theme_use(theme)

        return _built_func

    def _change_font(self, size):
        def _func():
            pixel_size = int(size / 100 * 13)
            for font in ("TkDefaultFont", "TkTextFont", "TkHeadingFont"):
                tkfont.nametofont(font).configure(size=pixel_size)
            self.master.style.configure('Treeview', rowheight=pixel_size+10)
            # TODO: edit to match the 100% -? ==> spacing is off and headingfont is smaller than DefualtFont
        return _func


class TabFiles(ttk.PanedWindow):
    def __init__(self, master, **kwargs):
        self._single_file_root = None
        super().__init__(master, orient=tk.HORIZONTAL, **kwargs)
        self.file_display = ttk.Treeview(self, column='#1')
        self.add(self.file_display)

        def OnDoubleClick(event):
            item = self.file_display.selection()
            selection = self.file_display.selection()
            if selection:
                confirm = messagebox.askokcancel('Caution',
                                                 f'Removing {", ".join(self.file_display.item(s, "text") for s in selection[:3])}\nIf this is not'
                                                 f' a bottom level entry, all entries within it will be removed as well'
                                                 f'. Are you sure you want to remove this?',
                                                 default='cancel')
                if confirm:
                    for i in item:
                        if i in ('I001', 'I002', 'I003'):
                            for children in self.file_display.get_children(i):
                                self.file_display.delete(children)
                        else:
                            self.file_display.delete(i)

        self.file_display.bind("<Double-1>", OnDoubleClick)

        self.file_display.heading('#0', text='Display Name')
        self.file_display.heading('#1', text='Path')

        self.treenode_base_files = self.file_display.insert('', 'end', text='Base Files')
        self.treenode_current_subs = self.file_display.insert('', 'end', text='Current Student Submissions')
        self.treenode_past_subs = self.file_display.insert('', 'end', text='Past Student Submissions')

        buttons_panel = ttk.Labelframe(self, text='Add Files')
        self.add(buttons_panel)
        buttons_padding_x = 10
        buttons_padding_y = 5
        ttk.Button(buttons_panel, text='Add Single File', command=(lambda: SingleFile(self))).pack(anchor='nw',
                                                                                                   padx=buttons_padding_x,
                                                                                                   pady=buttons_padding_y)
        ttk.Button(buttons_panel, text='Add Directory of Files', command=(lambda: DirectoryPath(self))).pack(
            anchor='nw', padx=buttons_padding_x,
            pady=buttons_padding_y)
        ttk.Button(buttons_panel, text='Add Directory of Zip Files', command=(lambda: ZipPath(self))).pack(anchor='nw',
                                                                                                           padx=buttons_padding_x,
                                                                                                           pady=buttons_padding_y)
        ttk.Button(buttons_panel, text='Add by Wildcard', command=(lambda: Wildcard(self))).pack(anchor='nw',
                                                                                                 padx=buttons_padding_x,
                                                                                                 pady=buttons_padding_y)

        ttk.Button(buttons_panel, text='Add Checkmate Directory', command=(lambda: CheckmatePath(self))).pack(
            anchor='nw', padx=buttons_padding_x,
            pady=buttons_padding_y)

    def update_tree(self, path, display_name_or_regex, file_type, selection_type, filename=''):
        assert selection_type in ('single', 'directory', 'directory_of_zip', 'wildcard', 'checkmate'), selection_type
        converter = {'Base Files': self.treenode_base_files,
                     'Past Student Submissions': self.treenode_past_subs,
                     'Current Student Submissions': self.treenode_current_subs}
        if selection_type != 'wildcard':
            path = pathlib.Path(path)
        if selection_type == 'wildcard':
            wildcard = self.file_display.insert(converter[file_type], 'end', text=path, values=(path,))
            regex = re.compile(display_name_or_regex)
            for file in glob.iglob(path, recursive=True):
                location = pathlib.Path(file)
                name = file
                name_temp = regex.match(name) if regex else None
                name = name_temp.group(1) if name_temp else name.name
                self.file_display.insert(wildcard, 'end', text=name, values=(location,))

        elif path.is_file():
            self.file_display.insert(converter[file_type], 'end', text=display_name_or_regex, values=(path,))
        else:
            directory = self.file_display.insert(converter[file_type], 'end',
                                                 text=f"{display_name_or_regex}{'_' if display_name_or_regex else ''}{path.name}" if selection_type == 'checkmate' else path.name,
                                                 values=(path,))
            keep_directory = False
            try:
                if selection_type == 'directory_of_zip':
                    temp_root = pathlib.Path(self.master.master.master.temp_dir)

                    # loops through all submissions
                    for submission in pathlib.Path.iterdir(path):
                        if not zipfile.is_zipfile(submission):
                            continue

                        keep_student = False
                        regex_match = re.match(display_name_or_regex, submission.name)
                        student = submission.name if not regex_match else regex_match.group(1)
                        student_tree_branch = self.file_display.insert(directory, 'end',
                                                                       text=student,
                                                                       values=(submission,))
                        temp_pointer = temp_root.joinpath(student)
                        temp_pointer.mkdir()

                        # unzips the code of current student

                        zip_ref = zipfile.ZipFile(path.joinpath(submission), 'r')
                        zip_ref.extractall(temp_pointer)
                        zip_ref.close()
                        for found_file in temp_pointer.iterdir():
                            if found_file.name == filename or filename == '':
                                self.file_display.insert(student_tree_branch, 'end',
                                                         text=f"{student}/{found_file.name}",
                                                         values=(found_file.as_posix(),))
                                keep_student = True
                                keep_directory = True
                        if not keep_student:
                            self.file_display.delete(student_tree_branch)
                    if not keep_directory:
                        self.file_display.delete(directory)
                        messagebox.showwarning('No files found', 'No zip files were found within selected directory')
                elif selection_type == 'checkmate':
                    temp_root = pathlib.Path(self.master.master.master.temp_dir)
                    for ucinetid in pathlib.Path(path).iterdir():
                        files_exist = False
                        if ucinetid.name == '.DS_Store':
                            continue
                        name = ucinetid.name
                        student_restructured_dir = temp_root.joinpath(
                            f"{display_name_or_regex}{'_' if display_name_or_regex else ''}{name}")  # TODO: test to see what happens when student did not submit any files
                        student_restructured_dir.mkdir()
                        student = self.file_display.insert(directory, 'end', text=name, values=(ucinetid.as_posix(),))
                        for submission_part in ucinetid.iterdir():
                            if submission_part.name == '.DS_Store':
                                continue
                            for file in submission_part.iterdir():
                                if file.is_file() and file.name != '.DS_Store':
                                    location = student_restructured_dir.joinpath(file.name)
                                    shutil.copy(file.as_posix(), location)
                                    self.file_display.insert(student, 'end',
                                                             text=f"{display_name_or_regex}{'_' if display_name_or_regex else ''}{name}/{file.name}",
                                                             values=(location,))
                                    files_exist = True
                        if not files_exist:
                            self.file_display.delete(student)
                else:
                    #  TODO: wrap text from tree
                    for found_file in pathlib.Path(path).iterdir():
                        if found_file.is_file() and found_file.name != '.DS_Store':
                            name = re.match(display_name_or_regex, found_file.name)
                            if name:
                                name = name.group(1)
                            else:
                                name = found_file.name
                            self.file_display.insert(directory, 'end', text=name, values=(path,))
            except OSError as e:
                self.file_display.delete(directory)
                tk.messagebox.showerror('Error',
                                        f'Aborting addition, ran into OSError:\n\n{e}\n\nEnsure You are using the correct file structure')


def popup_builder(name_filter_label: str, file_dialogue_function, selection_type: str, title: str):
    class _popup(TtkDialog):
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
                ttk.Label(window, text='Name of File in zipfile to submit').grid(column=0, row=2)
                ttk.Entry(window, textvariable=self.unzip_name).grid(column=1, row=2)

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
                    self.result = path, name, sub_type, selection_type, filename
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

    return _popup


SingleFile = popup_builder('Display Name: ', filedialog.askopenfilename, 'single', 'Add Single File')

DirectoryPath = popup_builder('RegEx (Display Name): ', filedialog.askdirectory, 'directory', 'Add Directory of Files')

ZipPath = popup_builder('RegEx (Display Name) from zip file: ', filedialog.askdirectory, 'directory_of_zip',
                        'Add Directory of Zip Files')

Wildcard = popup_builder('RegEx (Display Name): ', None, 'wildcard', 'Add files by Wildcard')

CheckmatePath = popup_builder('Prefix for Display Name', filedialog.askdirectory, 'checkmate',
                              'Add Checkmate Directory')


class EditSettingsPopup(TtkDialog):
    def __init__(self, parent):
        super().__init__(parent, title='Add Single File')

    def body(self, master):
        # TODO: Add other settings.
        window = ttk.Frame(master)
        window.pack(expand=1, fill='both')
        ttk.Label(master, text='Network Threshold').pack(side='top')
        vcmd = (self.register(self._validate_spin), '%P', '%S')
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

    def _validate_spin(self, total_string, single_change):
        if single_change.isdigit():
            return True
        else:
            self.bell()
            return False

    def apply(self):
        return self.result


class TabPartners(ttk.Frame):
    def __init__(self, master, **kwargs):
        padding = 5
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        # self.rowconfigure(0, weight=0)
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
        dynamic_settings_panel = ttk.Labelframe(self, text='Custom Parameters:')
        dynamic_settings_panel.grid(column=1, row=0, rowspan=2, sticky='news', padx=padding, pady=padding)
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
                    self.master.master.master.partners = partner_formatter(
                        **{argument: string_var.get() for argument, string_var in dynamic_kwargs.items()})
                    _repopulate_tree()

        ttk.Button(dynamic_settings_panel, text='Convert Selected File', command=_validate_and_convert).pack()

        # Display Found Partnerships
        def _repopulate_tree():
            # TODO: delete items in the tree first
            # TODO: if error, display error message through message box
            for entry in self.master.master.master.partners:
                entry = list(entry)
                self.found_partners_panel.insert('', 'end', entry, text=entry[0], values=entry[1])

        self.found_partners_panel = ttk.Treeview(self, column='#1')
        self.found_partners_panel.heading('#0', text='Student 1')
        self.found_partners_panel.heading('#1', text='Student 2')
        self.found_partners_panel.grid(column=0, row=1, sticky='news', padx=padding, pady=padding)


class TabSettings(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        sub_handler = ttk.Labelframe(self, text='Submission')
        sub_handler.pack(expand=0, fill='both', side='left', padx=10, pady=5)

        self.language = tk.StringVar(self)
        self.language.set(self.master.master.master.user_config['language'])
        ttk.Label(sub_handler, text='Language:', justify='left').pack(padx=5, pady=2.5, anchor='nw')
        ttk.OptionMenu(sub_handler, self.language, self.language.get(),
                       *sorted(self.master.master.master.moss.getLanguages())).pack(padx=5,
                                                                                    pady=2.5,
                                                                                    anchor='nw')

        ttk.Label(sub_handler, text='Moss ID:', justify='left').pack(padx=5, pady=2.5, anchor='nw')
        self.moss_id = tk.IntVar(self, self.master.master.master.user_config['moss_id'])
        vcmd = (self.register(self._validate_id), '%P', '%S')
        ttk.Entry(sub_handler, textvariable=self.moss_id, validate="key",
                  validatecommand=vcmd).pack(padx=5, pady=2.5,
                                             anchor='sw')  # TODO: on submit, check id length/validity?

        ttk.Label(sub_handler, text='Ignore Limit:', justify='left').pack(padx=5, pady=2.5, anchor='nw')
        self.ignore_limit = tk.IntVar(self)
        self.ignore_limit.set(self.master.master.master.user_config['ignore_limit'])
        vcmd_ignore = (self.register(self.validate_spin), '%P', '%S')
        self.ignore_limit_selector = ttk.Spinbox(sub_handler,
                                                 values=[i for i in range(0, 100)],
                                                 textvariable=self.ignore_limit,
                                                 validate='key',
                                                 validatecommand=vcmd_ignore)
        self.ignore_limit_selector.pack(padx=5, pady=2.5, anchor='nw')

        self.directory_mode_var = tk.BooleanVar(self, value=self.master.master.master.user_config['directory_mode'])
        self.directory_mode_checkbox = ttk.Checkbutton(sub_handler, text='Directory Mode',
                                                       variable=self.directory_mode_var)
        self.directory_mode_checkbox.pack(padx=5, pady=2.5, anchor='nw')

        report_handler = ttk.Labelframe(self, text='Report')
        report_handler.pack(expand=1, fill='both', side='right', padx=10, pady=5)

        self.archive_locally = tk.BooleanVar(self, self.master.master.master.user_config['archive'])
        self.zip_report = tk.BooleanVar(self, self.master.master.master.user_config['zip'])

        self.filter_report = tk.BooleanVar(self, self.master.master.master.user_config['filter'])
        ttk.Checkbutton(report_handler, text='Filter Report', variable=self.filter_report,
                        command=self._toggle_filter_settings).pack(padx=5, pady=2.5,
                                                                   anchor='nw')

        ttk.Label(report_handler, text='Network Lower Threshold:').pack(padx=20, pady=2.5, anchor='nw')
        self.network_threshold = tk.IntVar(self)
        self.network_threshold.set(self.master.master.master.user_config['network_threshold'])
        vcmd_spin = (self.register(self.validate_spin), '%P', '%S')
        self.network_threshold_selector = ttk.Spinbox(report_handler,
                                                      values=[i for i in range(0, 100)],
                                                      textvariable=self.network_threshold,
                                                      state=tk.NORMAL if self.filter_report.get() else tk.DISABLED,
                                                      validate='key',
                                                      validatecommand=vcmd_spin)
        self.network_threshold_selector.pack(padx=20, pady=2.5, anchor='nw')
        self.download_report = tk.BooleanVar(self, self.master.master.master.user_config['download_report'])
        ttk.Checkbutton(report_handler, text='Download Report', variable=self.download_report,
                        command=self._toggle_download_report).pack(padx=5, pady=2.5, anchor='nw')
        self.archive_locally_box = ttk.Checkbutton(report_handler, text='Archive Locally',
                                                   variable=self.archive_locally,
                                                   command=self._toggle_local_settings,
                                                   state=tk.ACTIVE if self.download_report.get() else tk.DISABLED)
        self.archive_locally_box.pack(padx=20, pady=2.5, anchor='nw')
        self.zip_button = ttk.Checkbutton(report_handler, text='Zip Report', variable=self.zip_report,
                                          state=tk.ACTIVE if self.archive_locally.get() else tk.DISABLED)
        self.zip_button.pack(padx=40, pady=2.5, anchor='nw')

    def validate_spin(self, total_string, single_change):
        if not total_string:
            self.network_threshold.set(0)
            return True
        if single_change.isdigit() and total_string and 0 <= int(total_string) < 100:
            return True
        else:
            self.bell()
            return False

    def _validate_ignore_limit(self, total_string, single_change):
        if not total_string:
            self.ignore_limit.set(0)
            return True
        if single_change.isdigit() and total_string and 0 <= int(total_string) <= 1000000:
            return True
        else:
            self.bell()
            return False

    def _validate_id(self, total_string, single_change):
        if single_change.isdigit() and len(total_string) <= 9:
            return True
        else:
            self.bell()
            return False

    def _toggle_local_settings(self):
        if self.archive_locally.get():
            self.zip_button.config(state=tk.ACTIVE)
        else:
            self.zip_report.set(False)
            self.zip_button.config(state=tk.DISABLED)

    def _toggle_filter_settings(self):
        if self.filter_report.get():
            self.master.tab(2, state=tk.NORMAL)
            self.network_threshold_selector.config(state=tk.NORMAL)
        else:
            self.master.tab(2, state=tk.DISABLED)
            self.network_threshold.set(0)
            self.network_threshold_selector.config(state=tk.DISABLED)

    def _toggle_download_report(self):
        if self.download_report.get():
            self.master.master.master.tab_submit.dir_entry.config(state=tk.ACTIVE)
            self.master.master.master.tab_submit.dir_button.config(state=tk.ACTIVE)
            self.master.master.master.tab_submit.review_button.config(state=tk.ACTIVE)
            self.archive_locally_box.config(state=tk.ACTIVE)
        else:
            self.archive_locally.set(False)
            self.master.master.master.tab_submit.dir_var.set('')
            self.master.master.master.tab_submit.review_before.set(False)
            self.master.master.master.tab_submit.dir_entry.config(state=tk.DISABLED)
            self.master.master.master.tab_submit.dir_button.config(state=tk.DISABLED)
            self.master.master.master.tab_submit.review_button.config(state=tk.DISABLED)
            self.archive_locally_box.config(state=tk.DISABLED)
        self._toggle_local_settings()


class TabSubmit(ttk.Frame):
    def __init__(self, master, **kwargs):
        padding = 5
        super().__init__(master, **kwargs)
        self.last_filtered_url = None
        self._save_dir = None

        # Tree config
        self.report_tree = ttk.Treeview(self, column=('s2', 'P', '%'))
        self.report_tree.heading('#0', text='Student 1')
        self.report_tree.column('#0', width=85)
        self.report_tree.column('s2', width=75)
        self.report_tree.column('P', width=75)
        self.report_tree.column('%', width=50)
        self.report_tree.heading('s2', text='Student 2')
        self.report_tree.heading('P', text='Partnered')
        self.report_tree.heading('%', text='Matched')
        self.report_tree.grid(column=0, row=0, rowspan=2, sticky='news')

        # Stats / Errors
        error_pane = ttk.Frame(self)
        error_pane.grid(column=0, row=3)
        self.stats_var = tk.StringVar(self)
        ttk.Label(error_pane, textvariable=self.stats_var).pack()

        # Upper Panel
        pre_submit = ttk.Labelframe(self, text='New Submission')
        pre_submit.grid(column=1, row=0, sticky='news')
        ttk.Label(pre_submit, text='Choose Directory').grid(column=0, row=0, padx=padding, pady=padding)
        self.dir_var = tk.StringVar(self)
        self.dir_entry = ttk.Entry(pre_submit, textvariable=self.dir_var,
                                   state=tk.ACTIVE if self.master.master.master.tab_settings.download_report.get() else tk.DISABLED)
        self.dir_entry.grid(column=1, row=0, padx=padding, pady=padding)
        self.dir_button = ttk.Button(pre_submit, text='Browse...', command=self._select_report_directory,
                                     state=tk.ACTIVE if self.master.master.master.tab_settings.download_report.get() else tk.DISABLED)
        self.dir_button.grid(column=2, row=0, padx=padding, pady=padding)
        self.review_before = tk.BooleanVar(self, self.master.master.master.user_config['review_before_archiving'])
        self.review_button = ttk.Checkbutton(pre_submit, text='Review Report before Archiving',
                                             variable=self.review_before,
                                             state=tk.ACTIVE if self.master.master.master.tab_settings.download_report.get() else tk.DISABLED)
        self.review_button.grid(column=0, row=1, columnspan=2, padx=padding, pady=padding)
        self.submit = ttk.Button(pre_submit, text='Submit', command=self.master.master.master.validate_and_send)
        self.submit.grid(column=0, row=2, padx=padding, pady=padding)

        self.archive_button = ttk.Button(pre_submit, text='Archive', command=print, state=tk.DISABLED)
        self.archive_button.grid(column=0, row=3, padx=padding, pady=padding)
        self.edit_settings = ttk.Button(pre_submit, text='Edit Settings', command=lambda: EditSettingsPopup(self),
                                        state=tk.DISABLED)
        self.edit_settings.grid(column=1, row=3, padx=padding, pady=padding)

        self.unlock = ttk.Button(pre_submit, text='Unlock', command=self.master.master.master.unlock_after_submit,
                                 state=tk.DISABLED)
        self.unlock.grid(column=1, row=2, padx=padding, pady=padding)

        # Lower Panel
        process_submission = ttk.Labelframe(self, text='Process Submission')
        process_submission.grid(column=1, row=1, sticky='news', padx=padding, pady=padding)
        ttk.Label(process_submission, text='Original URL: ').grid(column=0, row=0, padx=padding, pady=padding)
        ttk.Entry(process_submission, textvariable=self.master.master.master.url_var).grid(column=1, row=0,
                                                                                           padx=padding,
                                                                                           pady=padding)
        ttk.Button(process_submission, text='Filter Report', command=self.filter_url_report).grid(column=0, row=1,
                                                                                                  padx=padding,
                                                                                                  pady=padding)
        ttk.Button(process_submission, text='Archive Report', command=self.archive_url_report).grid(column=0, row=2,
                                                                                                    padx=padding,
                                                                                                    pady=padding)

        self.use_active_partners = tk.BooleanVar(self, False)
        self.use_active_files = tk.BooleanVar(self, False)
        ttk.Checkbutton(process_submission, text='Use active partners', variable=self.use_active_partners).grid(
            column=1, row=1, padx=padding,
            pady=padding, sticky='w')
        ttk.Checkbutton(process_submission, text='Use active files', variable=self.use_active_files).grid(column=2,
                                                                                                          row=1,
                                                                                                          padx=padding,
                                                                                                          pady=padding,
                                                                                                          sticky='w')
        ttk.Label(process_submission, text='Network Lower Threshold:').grid(column=1, row=2)
        self.network_threshold = tk.IntVar(self, 0)
        vcmd_spin = (self.register(self.master.master.master.tab_settings.validate_spin), '%P', '%S')
        self.network_threshold_selector = ttk.Spinbox(process_submission,
                                                      values=[i for i in range(0, 100)],
                                                      textvariable=self.network_threshold,
                                                      validate='key',
                                                      validatecommand=vcmd_spin)
        self.network_threshold_selector.grid(column=1, row=3)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=100,
                                            mode='determinate')
        self.progress_bar.grid(column=0, row=4, columnspan=2, sticky='news')
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def update_tree(self, passed_entries=None):
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        net_num = 1
        search_tree = self.master.master.master.moss.template_values.get('entries',
                                                                         []) if passed_entries is None else passed_entries
        if search_tree:
            network = self.report_tree.insert('', 'end', text='Network 1')
        else:
            network = None
        for index, match in enumerate(search_tree):
            if match is None:
                if index == len(search_tree) - 1:
                    continue
                net_num += 1
                network = self.report_tree.insert('', 'end', text=f'Network {net_num}')
            else:
                self.report_tree.insert(network, 'end', text=match['student1'],
                                        values=(match['student2'], match['partnered'], match['lines']))

    def _select_report_directory(self):
        selected_file = filedialog.askdirectory()
        if selected_file:
            self.dir_var.set(selected_file)

    def filter_url_report(self):
        m = model.MossUCI(self.master.master.master.tab_settings.moss_id.get(),
                          self.master.master.master.tab_settings.language.get())
        m.debug = self.master.master.master.menus.debug_mode
        m.sent = True
        m.url = self.master.master.master.url_var.get()
        if self.use_active_files.get():
            m.current_quarter_students = self.master.master.master.moss.current_quarter_students
        else:
            m.deactivate_current_students()
        partners = self.master.master.master.partners if self.use_active_partners.get() else ()
        try:
            m.filter_report(path=self.master.master.master.temp_dir, partners=partners, archive=False, zip_report=False,
                            network_threshold=self.network_threshold.get(), filter=True)
            self.last_filtered_url = m.url
        except (ValueError, ConnectionError) as e:
            messagebox.showerror('Error', e)
        self.update_tree(m.template_values.get('entries', []))

    def archive_url_report(self):
        save_dir = filedialog.askdirectory()
        if not save_dir:
            return
        else:
            self._save_dir = save_dir
            self.master.master.master.after(10, self._archive_helper)

    def _archive_helper(self):
        save_dir = self._save_dir
        url = self.master.master.master.url_var.get()
        url = url[:-1] if url.endswith('/') else url
        filtered = url == self.last_filtered_url
        m = model.MossUCI(self.master.master.master.tab_settings.moss_id.get(),
                          self.master.master.master.tab_settings.language.get())
        m.debug = self.master.master.master.menus.debug_mode
        m.sent = True
        m.url = url
        if filtered:
            if self.use_active_files.get():
                m.current_quarter_students = self.master.master.master.moss.current_quarter_students
            else:
                m.deactivate_current_students()
            partners = self.master.master.master.partners if self.use_active_partners.get() else ()
        else:
            partners = ()
            m.deactivate_current_students()
        try:
            m.filter_report(path=save_dir, partners=partners, archive=True, zip_report=False,
                            network_threshold=self.network_threshold.get(), filter=True)
        except (ValueError, ConnectionError) as e:
            messagebox.showerror('Error', e)
        self.update_tree(m.template_values.get('entries', []))


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


if __name__ == '__main__':
    app = UciMossGui()
    app.run()
    # TODO: Submission page has ability to modify settings (can preview before mass download; or decide to download after)
    # TODO: weight add files -> stretch horizontally
    # TODO: Remove partners

    # http://moss.stanford.edu/results/235519733
    # 10th assignment submission
