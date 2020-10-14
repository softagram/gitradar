import delegator


def run_cmd(cmd, cmd_title='', verbose=False):
    lines = []
    if verbose:
        print(cmd_title + '  : ' + cmd)
    for line in delegator.run(cmd).out.splitlines():
        lines.append(line.rstrip())
    return list(filter(lambda x: len(x) > 0, lines))
