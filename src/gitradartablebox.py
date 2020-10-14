import urwid

from gitradartable import GitRadarTable


class GitRadarTableBox(urwid.WidgetWrap):
    def __init__(self, columns_, logger, model, *args, **kwargs):
        self.table = GitRadarTable(columns_[:], self, model, *args, **kwargs)
        urwid.connect_signal(
            self.table, "select",
            lambda source, selection: logger.info(
                "selection: %s" % (selection)))
        label = "Files:%d pgsz:%s sort:%s%s hdr:%s ftr:%s ui_sort:%s cell_sel:%s" % (  # noqa
            self.table.query_result_count(),
            self.table.limit if self.table.limit else "-",
            "-" if self.table.sort_by[1] else "+" if self.table.sort_by[
                0] else "n",
            self.table.sort_by[0] or " ",
            "y" if self.table.with_header else "n",
            "y" if self.table.with_footer else "n",
            "y" if self.table.ui_sort else "n",
            "y" if self.table.cell_selection else "n",
        )
        self.pile = urwid.Pile([("pack", urwid.Text(label)),
                                ("pack", urwid.Divider(u"\N{HORIZONTAL BAR}")),
                                ("weight", 1,
                                 self.table)])
        self.box = urwid.BoxAdapter(urwid.LineBox(self.pile), 38)
        super(GitRadarTableBox, self).__init__(self.box)
        self.loop = None


def main():
    pass


if __name__ == "__main__":
    main()
