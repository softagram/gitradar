#!/usr/bin/python
import logging

logger = logging.getLogger(__name__)
from panwid.datatable import *
from urwid_utils.palette import *
import random
import string

from workspaceindex import analyze_changes, analyze_changes_unstaged_diff, \
    analyze_changes_staged_diff, \
    analyze_changes_in_commits_but_not_pushed_diff, \
    analyze_changes_in_recent_production_release_diff, \
    analyze_changes_pushed_but_not_merged_diff, \
    analyze_changes_in_merged_prs_not_released_diff


class DialogExit(Exception):
    pass


class DialogDisplay:
    palette = [
        ('body', 'black', 'light gray', 'standout'),
        ('border', 'black', 'dark blue'),
        ('shadow', 'white', 'black'),
        ('selectable', 'black', 'dark cyan'),
        ('focus', 'white', 'dark blue', 'bold'),
        ('focustext', 'light gray', 'dark blue'),
    ]

    def __init__(self, text, height, width, body=None):
        width = int(width)
        if width <= 0:
            width = ('relative', 80)
        height = int(height)
        if height <= 0:
            height = ('relative', 80)

        self.body = body
        if body is None:
            # fill space with nothing
            body = urwid.Filler(urwid.Divider(), 'top')

        self.frame = urwid.Frame(body, focus_part='footer')
        if text is not None:
            self.frame.header = urwid.Pile([urwid.Text(text), urwid.Divider()])
        w = self.frame

        # pad area around listbox
        w = urwid.Padding(w, ('fixed left', 2), ('fixed right', 2))
        w = urwid.Filler(w, ('fixed top', 1), ('fixed bottom', 1))
        w = urwid.AttrWrap(w, 'body')

        # "shadow" effect
        w = urwid.Columns([
            w,
            ('fixed', 2, urwid.AttrWrap(
                urwid.Filler(urwid.Text(('border', '  ')), "top"), 'shadow'))
        ])
        w = urwid.Frame(w, footer=urwid.AttrWrap(urwid.Text(('border', '  ')),
                                                 'shadow'))

        # outermost border area
        w = urwid.Padding(w, 'center', width)
        w = urwid.Filler(w, 'middle', height)
        w = urwid.AttrWrap(w, 'border')

        self.view = w

    def add_buttons(self, buttons):
        out = []
        for name, exitcode in buttons:
            b = urwid.Button(name, self.button_press)
            b.exitcode = exitcode
            b = urwid.AttrWrap(b, 'selectable', 'focus')
            out.append(b)
        self.buttons = urwid.GridFlow(out, 10, 3, 1, 'center')
        self.frame.footer = urwid.Pile([urwid.Divider(), self.buttons],
                                       focus_item=1)

    def button_press(self, button):
        raise DialogExit(button.exitcode)

    def main(self):
        self.loop = urwid.MainLoop(self.view, self.palette)
        try:
            self.loop.run()
        except DialogExit as e:
            return self.on_exit(e.args[0])

    def on_exit(self, exitcode):
        return exitcode, ""


class TextDialogDisplay(DialogDisplay):
    def __init__(self, text_lines, height, width):
        l = []
        # read the whole file (being slow, not lazy this time)
        for line in text_lines:
            l.append(urwid.Text(line.rstrip()))
        # noinspection PyTypeChecker
        body = urwid.ListBox(l)
        body = urwid.AttrWrap(body, 'selectable', 'focustext')

        DialogDisplay.__init__(self, None, height, width, body)

    def unhandled_key(self, size, k):
        if k in ('up', 'page up', 'down', 'page down'):
            self.frame.set_focus('body')
            self.view.keypress(size, k)
            self.frame.set_focus('footer')


class ActionButton(urwid.Button):
    def __init__(self, caption, callback):
        super(ActionButton, self).__init__("")
        urwid.connect_signal(self, 'click', callback)
        self._w = urwid.AttrMap(urwid.SelectableIcon(caption, 1), None,
                                focus_map='reversed')


class GitRadarTable(DataTable):
    columns = []
    index = "index"

    def __init__(self, columns_, parent, model, num_rows=10, *args, **kwargs):
        self.num_rows = num_rows
        self.parent = parent
        GitRadarTable.columns = columns_
        # indexes = random.sample(range(self.num_rows*2), num_rows)
        main_branch, dev_branch, stage_names, stage_shortnames = model
        self.main_branch = main_branch
        self.dev_branch = dev_branch
        self.stage_names = stage_names
        self.load_data()
        self.last_rec = len(self.query_data)
        super(GitRadarTable, self).__init__(*args, **kwargs)

    def load_data(self):
        self.main_branch = 'master'
        self.dev_branch = 'dev'
        stage_names, stage_data, filepaths = analyze_changes(self.main_branch,
                                                             self.dev_branch,
                                                             self.stage_names)
        stage_names_r = list(stage_names)
        stage_names_r.reverse()

        filedata = {}
        for stage_name, v in stage_data.items():
            for fp in v['filepaths']:
                filedata.setdefault(fp, {})[stage_name] = 'x'
        for fp in filepaths:
            if fp not in filedata:
                filedata[fp] = {}
                for s in stage_names:
                    filedata[fp][s] = 0
            else:
                for s in stage_names:
                    if s not in filedata[fp]:
                        filedata[fp][s] = 0

        indexes = list(range(len(filedata)))

        self.query_data = [
            self.fill_row(indexes[i], filepaths, stage_names, stage_data,
                          filedata)
            for i in range(len(filepaths))
            # self.random_row(i) for i in range(self.num_rows)
        ]
        random.shuffle(self.query_data)

    def fill_row(self, uniqueid, filepaths, stage_names, stage_data, filedata):
        filepath = filepaths[uniqueid]

        # filedata = {}
        # filedata[filepath] = {'unstaged': 1234, 'staged': 1234}

        def get_val(x):
            if x is None:
                return '_'
            if x != 'x':
                return ' '
            return x

        return dict(
            uniqueid=uniqueid,
            file=filepath,
            in_previous_production_release=get_val(
                filedata[filepath]['in_previous_production_release']),
            in_last_production_release=get_val(
                filedata[filepath]['in_last_production_release']),
            in_merged_prs_not_released=get_val(
                filedata[filepath]['in_merged_prs_not_released']),
            pushed_but_not_merged=get_val(
                filedata[filepath]['pushed_but_not_merged']),
            in_commits_but_not_pushed=get_val(
                filedata[filepath]['in_commits_but_not_pushed']),
            unstaged=get_val(filedata[filepath]['unstaged']),
            staged=get_val(filedata[filepath]['staged']),
            qux=urwid.Text([("red", "1"), ("green", "2"), ("blue", "3")]),
            xyzzy=("%0.1f" % (random.uniform(0, 100)) if random.randint(0,
                                                                        5) else None),
            file_len=lambda r: len(r["file"]) if r.get("file") else 0,
            # xyzzy = random.randint(10, 100),
            empty=None,
            a=dict(b=dict(c=random.randint(0, 100))),
            d=dict(e=dict(f=random.randint(0, 100))),
            color=["red", "green", "blue"][random.randrange(3)],
        )

    def query(self, sort=(None, None), offset=None, limit=None, load_all=False):

        logger.info(
            "query: offset=%s, limit=%s, sort=%s" % (offset, limit, sort))
        try:
            sort_field, sort_reverse = sort
        except:
            sort_field = sort
            sort_reverse = None

        if sort_field:
            kwargs = {}
            kwargs[
                "key"] = lambda x: (
                x.get(sort_field) is None, x.get(sort_field), x.get(self.index))
            if sort_reverse:
                kwargs["reverse"] = sort_reverse
            self.query_data.sort(**kwargs)
        if offset is not None:
            if not load_all:
                start = offset
                end = offset + limit
                r = self.query_data[start:end]
                logger.debug("%s:%s (%s)" % (start, end, len(r)))
            else:
                r = self.query_data[offset:]
        else:
            r = self.query_data

        for d in r:
            yield d

    def query_result_count(self):
        return self.num_rows

    def reset_layout(self):
        '''
        Resets the console UI to the default layout
        '''
        self.parent.loop.widget = self.parent._body
        self.parent.loop.draw_screen()

    def dialog(self, header, text=None):
        '''
        Overlays a dialog box on top of the console UI

        Args:
            header
            text (list): A list of strings to display
        '''

        if text is None:
            text = ['']
        text = [x + '\n' for x in text]
        number_of_rows = len(text) if len(text) > 5 else 5

        # Header
        header_text = urwid.Text(('banner', header), align='center')
        header = urwid.AttrMap(header_text, 'banner')

        # Body
        body_text = urwid.Text(text, align='left', wrap='any')
        body_filler = urwid.Filler(body_text, valign='middle')
        body_padding = urwid.Padding(body_filler, left=1, right=1)
        body = urwid.LineBox(body_padding)

        # Footer
        button = urwid.Button('OK', self.reset_layout())
        footer = urwid.AttrWrap(button, 'selectable', 'focus')
        footer = urwid.GridFlow([footer], 8, 1, 1, 'center')

        # Layout
        layout = urwid.Frame(body, header=header, footer=footer,
                             focus_part='footer')

        w = urwid.Overlay(
            urwid.LineBox(layout),
            self.parent._body,
            align='left',
            width=150,
            valign='middle',
            height=number_of_rows)
        urwid.connect_signal(button, 'click',
                             lambda button: self.reset_layout())
        self.parent.loop.widget = w

    def handle_activate(self, cell, selection):
        # Some debug prints that are useful with this complex UI lib
        # print('Selected: {}'.format(cell))
        # if index == 1:
        # print(selection.data["file"]+" unstaged="+selection.data["unstaged"])
        # if index == 2:
        #  print(selection.data["file"] + " staged=" + selection.data["staged"])
        #                logger.info(self.selection.data["staged"])
        # print(selection.column)
        # print(selection[1].column)
        # print(selection[2].column)
        # print(self.focus_position)
        # print(dir(selection))
        # print(self.focus)
        # print(selection.focus)
        # print(selection[0].cell_selection) -> True
        # print(selection.data["staged"])

        diffs = [
            ('unstaged', analyze_changes_unstaged_diff),
            ('staged', analyze_changes_staged_diff),
            (
                'commit',
                lambda x: analyze_changes_in_commits_but_not_pushed_diff(
                    self.dev_branch, x),
            ),
            (
                'review',
                lambda x: analyze_changes_pushed_but_not_merged_diff(
                    self.dev_branch,
                    self.main_branch, x),
            ), (
                'main',
                lambda x: analyze_changes_in_merged_prs_not_released_diff(
                    self.main_branch, x),
            ), (
                'prod',
                lambda x: analyze_changes_in_recent_production_release_diff(1,
                                                                            x),
            ), ('prod-1',
                lambda x: analyze_changes_in_recent_production_release_diff(2,
                                                                            x))
        ]

        alltext = ''
        for title, fetct_diff in diffs:
            diff1 = fetct_diff('../' + selection.data['file'])
            if diff1 is None or len(diff1) == 0:
                continue
            diff1 = diff1.replace(selection.data['file'], '')

            # widget = urwid.Text('U') #Unstaged changes for {}'.
            #    format(selection.data['file']))
            # tdd = widget # TextDialogDisplay(['qwer','asdf'], 50, 50)
            # tdd.add_buttons([("Exit", 0)])
            # self.parent.loop.widget = tdd
            # self.parent.loop.draw_screen()
            alltext += title + '\n' + diff1 + '\n\n'

        if len(alltext) > 0:
            self.dialog(' CHANGES OF ' + selection.data['file'],
                        alltext.split('\n'))

    def keypress(self, size, key):

        if key == "meta r":
            self.load_data()
            self.reset(reset_sort=True)
        if key == "ctrl r":
            self.reset(reset_sort=True)
        if key == "ctrl d":
            self.log_dump(20)
        if key == "meta d":
            self.log_dump(20, columns=["unstaged", "file"])
        if key == "ctrl f":
            self.focus_position = 0
        elif key == "ctrl t":
            # logger.info(self.get_row(0)[0])
            logger.info(self.selection.data["staged"])
        elif key == "meta i":
            logger.info(
                "unstaged %s, file: %s" % (self.selection.get("unstaged"),
                                           self.selection.get("file")))
        elif self.ui_sort and key.isdigit() and int(key) - 1 in range(
                len(self.columns)):
            col = int(key) - 1
            self.sort_by_column(col, toggle=True)
        elif key == "ctrl l":
            self.load("test.json")
        elif key == "ctrl s":
            self.save("test.json")
        elif key == "0":
            # self.sort_by_column(self.index, toggle=True)
            self.sort_index()
        elif key == "a":
            self.add_row(self.random_row(self.last_rec))
            self.last_rec += 1
        elif key == "A":
            self.add_row(self.random_row(self.last_rec), sort=False)
            self.last_rec += 1
        elif key == "d":
            if len(self) > 0:
                self.delete_rows(self.df.index[self.focus_position])
        elif key == "meta a":
            name = "".join(
                random.choice(
                    string.ascii_uppercase + string.ascii_lowercase + string.digits)
                for _ in range(5))
            data = [
                "".join(
                    random.choice(
                        string.ascii_uppercase + string.ascii_lowercase + string.digits)
                    for _ in range(5)) for _ in range(len(self))
            ]
            col = DataTableColumn(name, label=name, width=6, padding=0)
            self.add_columns(col, data=data)
        elif key == "r":
            self.set_columns(GitRadarTable.columns)
        elif key == "t":
            self.toggle_columns("qux")
        elif key == "T":
            self.toggle_columns(["unstaged", "file"])
        elif key == "D":
            self.remove_columns(len(self.columns) - 1)
        elif key == "f":
            self.apply_filters(
                [lambda x: x["unstaged"] > 20, lambda x: x["staged"] < 800])
        elif key == "F":
            self.clear_filters()
        elif key == ".":
            self.toggle_details()
        elif key == "s":
            self.selection.set_attr("red")
        elif key == "S":
            self.selection.clear_attr("red")
        elif key == "k":
            self.selection[2].set_attr("red")
        elif key == "K":
            self.selection[2].clear_attr("red")
        elif key == "u":
            logger.info(self.footer.values)
        elif key == "c":
            self.toggle_cell_selection()
        elif key == "shift left":
            self.cycle_sort_column(-1)
        elif key == "shift right":
            self.cycle_sort_column(1)
        elif self.ui_sort and key == "shift up":
            self.sort_by_column(reverse=True)
        elif self.ui_sort and key == "shift down":
            self.sort_by_column(reverse=False)
        elif key == "shift end":
            self.load_all()
            # self.listbox.focus_position = len(self) -1
        elif key == "ctrl up":
            if self.focus_position > 0:
                self.swap_rows(self.focus_position, self.focus_position - 1,
                               "unstaged")
                self.focus_position -= 1
        elif key == "ctrl down":
            if self.focus_position < len(self) - 1:
                self.swap_rows(self.focus_position, self.focus_position + 1,
                               "unstaged")
                self.focus_position += 1
        elif key == 'enter':
            s = self.selection
            self.handle_activate(None, s)
            """ This needs to be improved still...
            for i, cell in enumerate(s):
                # print(dir(cell))
                break
                if cell.normal_attr_map[None] != 'table_row_body':
                    # print(cell.normal_attr_map[None])
                    #break
                else:
                    print('==  {}'.format(cell.normal_attr_map[None]))
            """
        else:
            return super(GitRadarTable, self).keypress(size, key)


def main():
    pass


if __name__ == "__main__":
    main()
