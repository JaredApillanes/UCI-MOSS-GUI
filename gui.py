import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont
from tkinter import messagebox

import model
import json
from tempfile import TemporaryDirectory

from frames.welcome_page import WelcomePage
from frames.partners_frame import TabPartners
from frames.submit_frame import TabSubmit
from frames.settings_frame import TabSettings
from frames.files_frame import TabFiles

from dialogue_boxes.text_dialogue import TextPopup


class UciMossGui(tk.Tk):
    def __init__(self, *args, **kwargs):
        self.temp_dir = None
        self.partners = {}
        self.user_config = {}
        self.load_saved_settings()
        self.moss = model.MossUCI(self.user_config['moss_id'], self.user_config['language'])

        super().__init__(*args, **kwargs)
        self.fonts = {font: tkfont.nametofont(font).actual() for font in
                      ('TkDefaultFont', 'TkHeadingFont', 'TkTextFont')}
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
        self.user_config = {
            "moss_id": 0,
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
        self.tab_settings.moss_id.set(self.user_config['moss_id'])
        self.tab_settings.language.set(self.user_config['language'])
        self.tab_settings.archive_locally.set(self.user_config['archive'])
        self.tab_settings.filter_report.set(self.user_config['filter'])
        self.tab_settings.network_threshold.set(self.user_config['network_threshold'])
        self.tab_settings.network_threshold_selector.config(state=tk.DISABLED)
        self.tab_settings.zip_report.set(self.user_config['zip'])
        self.tab_settings.zip_button.config(state=tk.DISABLED)
        self.tab_settings.ignore_limit.set(self.user_config['ignore_limit'])
        self.tab_settings.download_report.set(self.user_config['download_report'])
        self.tab_settings.directory_mode_var.set(self.user_config['directory_mode'])
        self.welcome_page.disable_welcome_var.set(self.user_config['disable_welcome'])
        self.tab_submit.review_before.set(self.user_config['review_before_archiving'])
        self.tab_submit.review_button.config(state=tk.DISABLED)
        self.style.theme_use(self.user_config['theme'])

    def run(self):
        with TemporaryDirectory(dir='.') as temp_dir:
            self.temp_dir = temp_dir
            aspect_ratio = 16 / 9
            screen_space = 0.45
            if aspect_ratio > 1:
                # width is handled first, and height is adjusted accordingly
                width = self.winfo_screenwidth() * screen_space
                height = width / aspect_ratio
            else:
                # height first, width second
                height = self.winfo_screenheight() * screen_space
                width = height * aspect_ratio

            self.geometry(
                f"{int(width)}x{int(height)}+{int(self.winfo_screenwidth() / 2 - width / 2)}+"
                f"{int(self.winfo_screenheight() / 2 - height / 2)}")
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

        def sifter(tree_item, add_function):
            if self.tab_files.file_display.get_children(tree_item):
                for sub_item in self.tab_files.file_display.get_children(tree_item):
                    sifter(sub_item, add_function)
            else:
                add_function(self.tab_files.file_display.item(tree_item, "values")[0],
                             self.tab_files.file_display.item(tree_item, "text").replace(' ', r'_'))

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
            self.tab_submit.unlock.config(state=tk.DISABLED)
            self.tab_submit.submit.config(state=tk.ACTIVE)
            self.tab_submit.progress_bar.stop()
            messagebox.showerror('Connection Error',
                                 'Ensure you have a valid moss ID entered in the Settings Tab, and that you have added '
                                 'files to send.')
            return
        else:  # Valid Report
            self.url_var.set(url)
            if not config['review_before_archiving']:  # Handle now...
                if not config['download_report']:
                    config['directory'] = self.temp_dir
                self.moss.filter_report(path=config['directory'], partners=self.partners,
                                        archive=config['archive'],
                                        zip_report=config['zip'],
                                        network_threshold=config['network_threshold'], to_filter=config['filter'])
            else:  # else prime others to handle
                self.tab_submit.archive_button.config(state=tk.ACTIVE)
                if config['filter']:
                    self.tab_submit.edit_settings.config(state=tk.ACTIVE)
                self.moss.filter_report(self.temp_dir, self.partners, False, False, config['network_threshold'],
                                        config['filter'])
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
            for name, font in self.master.fonts.items():
                tkfont.nametofont(name).configure(size=int(font['size'] * (size / 100)))
            self.master.style.configure('Treeview',
                                        rowheight=int(self.master.fonts['TkDefaultFont']['size'] * (size / 45)))

        return _func


if __name__ == '__main__':
    app = UciMossGui()
    app.run()
    # TODO: Remove partners
