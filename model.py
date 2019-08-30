import re
import datetime
import pathlib
import time
from urllib.request import urlopen
from collections import defaultdict
from shutil import make_archive

import mosspy
import jinja2

MOSSACCOUNT = 563499553
# TODO: remove personal account number
BASE_URL = 'http://moss.stanford.edu/results/'


def lock_after_send(f):
    """
    Method decorator for locking methods once the self.sent attribute
    is set to True
    :param f: function object
    :return: modified function with sent lock attached before function
             call
    """

    def _func(self, *args, **kwargs):
        """
        Raises an error if the 'sent' attribute in self is True,
            otherwise, passes args and kwargs to stored function
        :param self: class instance
        :param args: positional arguments
        :param kwargs: keyword arguments
        :return: call to stored function
        """
        if self.sent:
            raise ConnectionRefusedError('Files already sent')
        else:
            return f(self, *args, **kwargs)

    return _func


class MossUCI(mosspy.Moss):
    """
    A modified version of the Moss handler class built to streamline
    the filtration process across academic quarters and account for
    duplicate submissions resulting from peer-programming while
    increasing readability of presented data.
    """

    def __init__(self, account_number: int, language: str, debug=False):
        """
        :param account_number: Obtained from the email-process at http://moss.stanford.edu/
        :param language: As listed in the original MOSS instructions
        :param debug: Turn on or off print statements while running (shows progress during lengthy downloads)
        """
        mosspy.Moss.__init__(self, account_number, language)
        self.current_quarter_students = set()
        self.sent = False
        self.url = None
        self.debug = debug
        self.template_values = dict()
        self.cur_stu_deactivated = False

    def deactivate_current_students(self):
        self.cur_stu_deactivated = True

    def activate_current_students(self):
        self.cur_stu_deactivated = False

    def filter_report(self, path: str, partners=(('', ''),), archive=False, zip_report=False, network_threshold=-1,
                      filter=True):
        """
        Based off of the information loaded into the class instance
            (ie. the current vs. old students and report url), cache
            the corresponding report and parse it based off of the
            following criteria:
            1. Create networks of matches based off of reachability between matches
                ex: if student A is matched with student B and student B matches
                    with student C, then the network {A, B, C) exists.
            2. Filter out networks that do not contain any current students,
                based off of the student's status of current or old student
                (established when loading the files into the class instance),
            3. Remove networks of single matches between partners, based off
                of the array of partners loaded in the filter_report call.
            4. Generate a report.html file with the generated information:
                Networks are separated by horizontal lines and sorted by
                decreasing importance.
                Matches between partners are marked as such.
            5. Download dependent resources if indicated within the
                filter_report call.
            6. Compress the entire directory if indicated within the
                filter_report call.
        :param path: string storing a path to an existing directory to generate the report in.
        :param partners: an iterable object of two tuples (that supports the self.__contains__ call)
                        that represents partners
        :param archive: boolean value indicating whether or not to archive dependent information for the report.
        :param zip_report: boolean value indicating whether or not to compress the directory once finished.
        :param network_threshold: set a line-based threshold to filter networks (removes matches
                                    under the given threshold)
        :param filter: boolean value indicating whether or not to filter the report or not (allowing for archival of
                        original report)
        :return: None
        """
        # Setup and check assertions
        if self.debug:
            print('begin archiving...')
        if not self.sent or not self.url:
            raise ConnectionAbortedError('Nothing sent; nothing to download')
        path = pathlib.Path(path)
        assert path.exists(), f'Path {path.as_posix()} does not exist.'
        assert path.is_dir(), f'Path {path.as_posix()} does not lead to a directory.'

        def _reachable(graph: {str: {str}}, start: str) -> {str}:
            reached_set, exploring_list = set(), [start]
            while exploring_list:
                node_to_explore = exploring_list.pop(0)
                reached_set.add(node_to_explore)
                exploring_list += [node for node in graph.get(node_to_explore, []) if node not in reached_set]
            return reached_set

        if len(self.url) == 0:
            raise Exception("Empty url supplied")

        # Parse URL
        result_id = self.url.split('/')[-1]
        self.template_values['resultID'] = result_id

        # Load Data
        if self.debug:
            print(result_id)
            print('opening base url...')
        response = urlopen(self.url)
        content = response.read().decode('utf-8')

        # Scrape Option info, date
        # TODO: Scrape error msgs
        if self.debug:
            print('parsing data...')
        self.template_values['date_info'] = re.search(r'Moss Results<p>\s(?P<date>.+)\s<p>\sOptions',
                                                      content).group('date')

        self.template_values['option_info'] = re.search(r'<p>\sOptions (?P<options>.+)\s<HR>', content).group('options')

        self.template_values['error_info'] = 'Not Implemented Yet'

        # Scrape mathes
        content = content.lower()
        click_pattern = re.compile(
            r'<tr><td><a href=\"(?P<url>http://moss\.stanford\.edu/results/\d+/match(?P<match_num>\d+)\.html)\">(?P<student1>.+) \((?P<perc1>\d{1,2})%\)</a>\s*<td><a href=\"http://moss\.stanford\.edu/results/\d+/match\d+\.html\">(?P<student2>.+) \((?P<perc2>\d{1,2})%\)</a>\s*<td align=right>(?P<lines>\d+)')
        matches = re.findall(click_pattern, content)

        if filter:
            # Generate connection network
            student_graph = defaultdict(set)
            for pair in matches:
                student_graph[pair[2]].add(pair[4])
                student_graph[pair[4]].add(pair[2])
            if self.debug:
                print('generating networks...')

            # Filter network by current quarter and remove networks of just partners
            networks = tuple(
                {frozenset(network) for network in [_reachable(student_graph, student) for student in student_graph]
                 if (self.cur_stu_deactivated or any(
                    student in self.current_quarter_students for student in network)) and network not in partners})

            student_lookup = {student: {match[1] for match in matches if student in match} for web in networks for
                              student
                              in web}

            match_line_lookup = {match_num: int(matches[match_num][6]) for match_num in range(len(matches))}

            # Cycle through matches (to retain order) and retrieve scraped match data
            self.template_values['entries'] = []
            if self.debug:
                print('creating template...')

            # added line if matches[int(match_number)] >= network_threshold
            # added [group for group in {} if group]
            network_by_matches = [
                sorted(
                    [group for group in {match_number for student in net for match_number in student_lookup[student] if
                                         int(matches[int(match_number)][3]) >= network_threshold or int(
                                             matches[int(match_number)][5]) >= network_threshold} if group],
                    key=(lambda entry: -match_line_lookup[int(entry)])) for net in networks]
            network_by_matches = [net for net in network_by_matches if net != []]
            network_by_matches = sorted(network_by_matches,
                                        key=(
                                            lambda entry: max(entry,
                                                              key=(lambda ent: match_line_lookup.get(int(ent), 0)))))
        else:
            self.template_values['entries'] = []
            network_by_matches = [[num for num in range(len(matches))]]
        for group_num, network in enumerate(network_by_matches):
            for match_num in network:
                url, match_num, student1, perc1, student2, perc2, lines, = matches[int(match_num)]
                self.template_values['entries'].append({'student1': student1,
                                                        'student2': student2,
                                                        'perc1': perc1,
                                                        'perc2': perc2,
                                                        'lines': lines,
                                                        'url': pathlib.Path(f'group{group_num}').joinpath(
                                                            f'match{match_num}.html') if archive else
                                                        f"http://moss.stanford.edu/results/{result_id}/match{match_num}.html",
                                                        'partnered': 'Y' if frozenset(
                                                            (student1,
                                                             student2)) in partners else ''})
            self.template_values['entries'].append(None)

        # Create directory for report
        directory = path.joinpath('moss_report__' + str(datetime.datetime.now().timestamp()).replace('.', '_'))
        directory.mkdir()

        # Download match resources (if archiving locally)
        if archive:
            if self.debug:
                print('Saving Resources...')
            for net, network in enumerate(network_by_matches):
                directory.joinpath('group' + str(net)).mkdir()
                for match_id in network:
                    for resource in ('', '-0', '-1', '-top'):
                        f = open(directory.joinpath(
                            pathlib.Path('group' + str(net)).joinpath('match' + match_id + resource + '.html')), 'w')
                        resource_contents = urlopen(
                            f'{BASE_URL}{result_id}/match{match_id}{resource}.html').read().decode()
                        if resource == '-top':
                            resource_contents = resource_contents.replace(
                                f'http://moss.stanford.edu/results/{result_id}/', '')
                        f.write(resource_contents)
                        f.close()
                        # Timeout to avoid being marked as spam by server
                        # time.sleep(0.1)

        self.template_values['original_length'] = len(matches)
        self.template_values['modified_length'] = len([num for net in network_by_matches for num in net])
        self.template_values['filtered'] = self.template_values['original_length'] - self.template_values[
            'modified_length']

        # Write Data to report
        if self.debug:
            print('loading template...')
        env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
        template = env.get_template('index.html')
        if self.debug:
            print('Generating report index...')
        with directory.joinpath('report.html').open('w') as report:
            report.write(template.render(self.template_values))
        if self.debug:
            print(f'Finished Generating Report: {directory.joinpath("report.html")}')

        # Zip Report directory and delete uncompressed director
        if zip_report:
            if self.debug:
                print('compressing report...')
            make_archive(directory, 'zip', directory)
            if self.debug:
                print('deleting un-ziped archive')
            directory.rmdir()

    @lock_after_send
    def addFile(self, file_path: str, display_name: str):
        """
        Calls super.addFile with corresponding information.
        Adds the display_name to a list of students to keep during
            the filtration process.
        :param file_path: string representing a path to the desired file.
        :param display_name: string representing the name to display for the file.
        :return: None
        """
        if self.debug:
            print(f'adding file: {display_name if display_name else file_path}')
        self.current_quarter_students.add(
            display_name if display_name else re.search(r'_(?P<uciID>\w+)uci\.edu', file_path).group('uciID'))
        super(MossUCI, self).addFile(file_path, display_name)

    @lock_after_send
    def add_old_students(self, file_path: str, display_name: str):
        """
        Calls super.addFile with corresponding information.
            Does not add students to the current_quarter list and
            therefore ignores students added by this method during
            report generation.
        :param file_path: string representing a path to the desired file.
        :param display_name: string representing the name to display for the file.
        :return: None
        """
        if self.debug:
            print(f'adding file: {display_name if display_name else file_path}')
        mosspy.Moss.addFile(self, file_path, display_name)

    @lock_after_send
    def send(self) -> str:
        """
        Calls super.send, but also sets the sent attribute to True and
            sets the url attribute to the returning information.
        :return: URL as string
        """
        if self.debug:
            print('sending submission...')
        self.url = mosspy.Moss.send(self)
        self.sent = True
        return self.url

    @lock_after_send
    def set_language(self, language: str):
        if language in self.languages:
            self.options["l"] = language
