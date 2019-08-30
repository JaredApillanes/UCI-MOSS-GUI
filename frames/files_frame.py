import tkinter as tk
import tkinter.ttk as ttk
import pathlib
from tkinter import messagebox, filedialog
import dialogue_boxes.dynamic_constructor as dynamic_constructor
import glob
import re
import shutil
import zipfile

SingleFile = dynamic_constructor.popup_builder('Display Name: ', filedialog.askopenfilename, 'single',
                                               'Add Single File')

DirectoryPath = dynamic_constructor.popup_builder('RegEx (Display Name): ', filedialog.askdirectory, 'directory',
                                                  'Add Directory of Files')

ZipPath = dynamic_constructor.popup_builder('RegEx (Display Name) from zip file: ', filedialog.askdirectory,
                                            'directory_of_zip',
                                            'Add Directory of Zip Files')

Wildcard = dynamic_constructor.popup_builder('RegEx (Display Name): ', None, 'wildcard', 'Add files by Wildcard')

CheckmatePath = dynamic_constructor.popup_builder('Prefix for Display Name', filedialog.askdirectory, 'checkmate',
                                                  'Add Checkmate Directory')


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
