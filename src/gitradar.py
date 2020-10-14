# noinspection PyUnresolvedReferences
import logging
import os
from optparse import OptionParser

from panwid.datatable import *
from panwid.listbox import ScrollingListBox
from urwid_utils.palette import *

from environmentindex import build__environment__version, \
    build__version__commit
from gitradartablebox import GitRadarTableBox
from stages import stage_names, stage_shortnames
from workspaceindex import analyze_changes


def init_settings(main_branch='', dev_branch=''):
    if main_branch == '':
        main_branch = 'master'
    if dev_branch == '':
        dev_branch = 'dev'

    return main_branch, dev_branch, stage_names, stage_shortnames


def shorten_env_name(name):
    if len(name) > 5:
        name = name[0:5] + '..'
    return name


def get_env_names_with_version(version, environment__version):
    envs = []
    for env, env_ver in environment__version.items():
        if env_ver.lstrip('v') == version.lstrip('v'):
            envs.append(env)
    return envs


def get_possible_matching_envs(environment__version, version__environments,
                               commit__versions,
                               stage_data, version):
    envs = set()
    if 'commits' in stage_data:
        if len(stage_data['commits']) > 0:
            latest_commit = stage_data['commits'][0]
            if latest_commit in commit__versions:
                for version in commit__versions[latest_commit]:
                    if version in version__environments:
                        for environment in version__environments[version]:
                            envs.add(environment)

    if version:
        envs.update(get_env_names_with_version(version, environment__version))

    if len(envs) > 0:
        return ' ' + ' '.join(
            map(lambda x: shorten_env_name(x.split('.')[0]), sorted(envs)))
    return ''


def invert_dict(x):
    y = {}
    for k, v in x.items():
        if v in y:
            y[v].append(k)
        else:
            y[v] = [k]
    return y


def main():
    os.system('echo "Running git fetch" && git fetch')
    os.system('echo "Running git fetcth upstream" && git fetch upstream')
    logger = logging.getLogger(__name__)
    parser = OptionParser()
    parser.add_option("-d", "--dir", dest="dir", help="git repo dir",
                      metavar="DIR")
    parser.add_option("-v", "--verbose", action="count", default=0),
    parser.add_option("-e", "--environment", action="append",
                      dest="environments"),
    parser.add_option('-D', '--debug', action="store_true", default=True)
    (options, args) = parser.parse_args()
    os.chdir(options.dir)
    envs = options.environments if options.environments is not None else []

    model = init_settings()
    main_branch, dev_branch, stage_names, stage_shortnames = model
    stage_names, stage_data, filepaths = analyze_changes(main_branch,
                                                         dev_branch,
                                                         stage_names)

    def map_version_to_tag(version):
        if version.startswith('v'):
            return version[1:]
        return version

    environment__version = build__environment__version(envs,
                                                       map_version_to_tag)
    version__environments = invert_dict(environment__version)
    version__commit = build__version__commit(environment__version)
    commit__versions = invert_dict(version__commit)

    last_prod_version = stage_data['in_last_production_release'][
        'version_number']
    prev_prod_version = stage_data['in_previous_production_release'][
        'version_number']

    if options.debug:
        for s in stage_names:
            for k, v in stage_data[s].items():
                if k == 'commits':
                    pass  # for commit in v:
                    # print('Stage: ' + stage_shortnames[s] + ': ' + commit)
                elif k == 'filepaths':
                    if options.verbose:
                        for filepath in v:
                            print('Stage: ' + stage_shortnames[
                                s] + ': ' + filepath)
                    print('Stage {}: {} files modified.'.format(
                        stage_shortnames[s], len(v)))

        # sys.exit(2)

    if options.verbose:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)8s] %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S')
        fh = logging.FileHandler("datatable.log")
        # fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        if options.verbose > 1:
            logger.setLevel(logging.DEBUG)
            logging.getLogger("panwid.datatable").setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
            logging.getLogger("panwid.datatable").setLevel(logging.INFO)
        logger.addHandler(fh)
        logging.getLogger("panwid.datatable").addHandler(fh)
        # logging.getLogger("raccoon.dataframe").setLevel(logging.DEBUG)
        # logging.getLogger("raccoon.dataframe").addHandler(fh)

    attr_entries = {}
    for attr in ["dark red", "dark green", "dark blue"]:
        attr_entries[attr.split()[1]] = PaletteEntry(
            mono="white", foreground=attr, background="black")
    entries = ScrollingListBox.get_palette_entries()
    entries.update(DataTable.get_palette_entries(user_entries=attr_entries))
    palette = Palette("default", **entries)

    screen = urwid.raw_display.Screen()
    # screen.set_terminal_properties(1<<24)
    screen.set_terminal_properties(256)

    NORMAL_FG_MONO = "white"
    NORMAL_FG_16 = "light gray"
    NORMAL_BG_16 = "black"
    NORMAL_FG_256 = "light gray"
    NORMAL_BG_256 = "g0"

    def env_matcher(stage):
        return get_possible_matching_envs(environment__version,
                                          version__environments,
                                          commit__versions, stage_data[stage],
                                          None)

    e1 = env_matcher('in_previous_production_release')
    e2 = env_matcher('in_last_production_release')
    e3 = env_matcher('pushed_but_not_merged')
    e4 = env_matcher('in_merged_prs_not_released')
    COLUMNS = [
        # DataTableColumn("uniqueid", width=10, align="right", padding=1),
        DataTableColumn("file", label="File", width=78),
        DataTableColumn(
            "unstaged",
            label=stage_shortnames['unstaged'],
            width=10,
            align="right",
            sort_key=lambda v: (v is None, v),
            attr="color",
            padding=0,
            footer_fn=lambda column, values: sum(
                v for v in values if v is not None)),
        DataTableColumn(
            "staged",
            label=stage_shortnames['staged'],
            width=10,
            align="right",
            sort_reverse=True,
            sort_icon=False,
            padding=1),  # margin=5),
        DataTableColumn(
            "in_commits_but_not_pushed",
            label=stage_shortnames['in_commits_but_not_pushed'],
            width=10,
            align="right",
            sort_reverse=True,
            sort_icon=False,
            padding=1),  # margin=5),
        DataTableColumn(
            "pushed_but_not_merged",
            label=stage_shortnames['pushed_but_not_merged'] + e3,
            width=10,
            align="right",
            sort_reverse=True,
            sort_icon=False,
            padding=1),  # margin=5),
        DataTableColumn(
            "in_merged_prs_not_released",
            label=stage_shortnames['in_merged_prs_not_released'] + e4,
            width=10,
            align="right",
            sort_reverse=True,
            sort_icon=False,
            padding=1),  # margin=5),
        DataTableColumn(
            "in_last_production_release",
            label=stage_shortnames[
                      'in_last_production_release'] + ' ' + last_prod_version + e2,
            width=10,
            align="right",
            sort_reverse=True,
            sort_icon=False,
            padding=1),  # margin=5),
        DataTableColumn(
            "in_previous_production_release",
            label=stage_shortnames[
                      'in_previous_production_release'] + ' ' + prev_prod_version + e1,
            width=10,
            align="right",
            sort_reverse=True,
            sort_icon=False,
            padding=1),  # margin=5),
        DataTableColumn(
            "qux",
            label=urwid.Text([("red", "q"), ("green", "u"), ("blue", "x")]),
            width=5,
            hide=True),
        # DataTableColumn("empty", label="empty", width=5),
    ]

    def detail_fn(data):

        return urwid.Padding(
            urwid.Columns([
                ("weight", 1, data.get("qux")),
                ("weight", 1, urwid.Text(str(data.get("file_len")))),
                ("weight", 1, urwid.Text(str(data.get("xyzzy")))),
            ]))

    grtb = GitRadarTableBox(
        COLUMNS,
        logger,
        model,
        33,
        index="uniqueid",
        detail_fn=detail_fn,
        # detail_column="staged", outcommented by Ville 2020/09
        cell_selection=True,
        sort_refocus=True,
        sort_by="file")

    boxes = [grtb]

    grid_flow = urwid.GridFlow(boxes, 300, 1, 1, "left")

    def global_input(key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        else:
            return False

    old_signal_keys = screen.tty_signal_keys()
    undef = list(old_signal_keys)
    undef[0] = 'undefined'
    undef[3] = 'undefined'
    undef[4] = 'undefined'
    
    # Outcommenting tty_signal_keys call that fails with recent Python 3.8 urwid-2.1.1
    #     TypeError: tcsetattr: elements of attributes must be characters or integers
    #
    # screen.tty_signal_keys(undef)

    main_frame = urwid.Frame(
        urwid.Filler(urwid.LineBox(grid_flow), valign="top"))
    main = urwid.MainLoop(
        main_frame,
        palette=palette,
        screen=screen,
        unhandled_input=global_input)

    try:
        grtb.loop = main
        grtb._body = main_frame
        main.run()
    finally:
        screen.tty_signal_keys(*old_signal_keys)


if __name__ == "__main__":
    main()
