"""
Use the following structure to implement your own converter.
This file must include a function 'partner_formatter' that
has at least one parameter 'path_to_csv' that will be passed
the string path to the partner file. The function must return
a set or similar container holding the student pairs.

IMPORTANT:
        These names must match the submission names.
"""


def partner_formatter(path_to_csv: str, assignment_number: str) -> {(str, str), }:
    """
    Generates a list of two-sets from a comma-separated-value file
        representing partners.
    Assumes the column structure:
        "StudentID","UCInetID","Last Name","First Name","Lab","1","2","3","4","5","6","7","8","9","10"
    :param path_to_csv: file path
    :param assignment_number: assignment to look at
    :return: list of partners
    """
    assignment_number = int(assignment_number)
    a_set = set()
    with open(path_to_csv, 'r') as part_file:
        for line in part_file:
            line = line.rstrip()
            if line == '"StudentID","UCInetID","Last Name","First Name","Lab","1","2","3","4","5","6","7","8","9","10"':
                continue
            line = line.split(',')
            a_set.add(frozenset((line[1].strip('"'), line[assignment_number + 4].strip('"').split('@')[0])))
    return a_set
