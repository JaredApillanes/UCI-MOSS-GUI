import tkinter as tk
import tkinter.ttk as ttk


class WelcomePage(ttk.Frame):

    def __init__(self, master):
        super().__init__(master)
        welcome_title = ttk.Label(self, text="Welcome", font=('', 30))
        welcome_title.pack(pady=10, padx=10)

        introduction = ttk.Label(self, justify=tk.CENTER,
                                 text='A GUI for the command line tool "Moss" developed by Alex Aiken.'
                                      '\n\nAn Extension for the file selection and report filtration system.'
                                      '\n\nSee the About and Help pages in the Info menu for more information.'
                                      '\n\n\nPLEASE NOTE:'
                                      '\n\nThis GUI is still in development and will be frequently '
                                      'updated. Please ensure you have the latest version.'
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
