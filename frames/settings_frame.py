import tkinter as tk
import tkinter.ttk as ttk


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
