import model

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import messagebox


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
