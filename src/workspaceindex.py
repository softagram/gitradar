""" Get information about the relevant changes worked on right now.
"""
import inspect
import os

# noinspection PyPackageRequirements
import delegator

debug = True


def run_cmd(cmd, cmd_title=''):
    lines = []
    if debug:
        print(cmd_title + '  : ' + cmd)
    for line in delegator.run(cmd).out.splitlines():
        lines.append(line.rstrip())
    return list(filter(lambda x: len(x) > 0, lines))


def analyze_changes_unstaged():
    filepaths = map_paths(
        run_cmd('git diff --name-only', inspect.stack()[0][0].f_code.co_name))
    return {'filepaths': filepaths, 'commits': []}


def analyze_changes_unstaged_diff(fp):
    return '\n'.join(
        run_cmd('git diff ' + fp, inspect.stack()[0][0].f_code.co_name))


def analyze_changes_staged():
    filepaths = map_paths(
        run_cmd('git diff --name-only --cached',
                inspect.stack()[0][0].f_code.co_name))
    return {'filepaths': filepaths, 'commits': []}


def analyze_changes_staged_diff(fp):
    return '\n'.join(run_cmd('git diff --cached ' + fp,
                             inspect.stack()[0][0].f_code.co_name))


def analyze__in_commits_but_not_pushed(devbranch):
    # TODO Make this detect current branch instead of parameterizing
    filepaths = map_paths(
        run_cmd('git diff origin/{}..HEAD --name-only'.format(devbranch),
                inspect.stack()[0][0].f_code.co_name))
    commits_not_pushed = run_cmd(
        'git log --format=format:%H origin/{}..HEAD'.format(devbranch),
        inspect.stack()[0][0].f_code.co_name)
    return {'filepaths': filepaths, 'commits': commits_not_pushed}


def analyze_changes_in_commits_but_not_pushed_diff(devbranch, fp):
    return '\n'.join(
        run_cmd('git diff origin/{}..HEAD {}'.format(devbranch, fp),
                inspect.stack()[0][0].f_code.co_name))


def analyze__in_commits(commit_ids):
    filepaths = []
    for commit_id in commit_ids:
        filepaths += map_paths(
            run_cmd(f'git diff --name-only {commit_id}^ {commit_id}',
                    inspect.stack()[0][0].f_code.co_name))
    return {'filepaths': filepaths, 'commits': commit_ids}


def analyze_changes_in_commits_diff(commit_ids, fp):
    status = analyze__in_commits(commit_ids)
    if fp.replace('../', '') in status['filepaths']:
        out = ''
        for commit_id in commit_ids:
            out += '\n'.join(
                run_cmd(f'git show {commit_id} {fp}',
                        inspect.stack()[0][0].f_code.co_name))
        return out


def analyze__in_branch(branch, main_branch, remote):
    remote_and_slash = ''
    if remote:
        remote_and_slash = remote + '/'
    filepaths = map_paths(
        run_cmd(
            f'git diff --name-only {branch}..{remote_and_slash}{main_branch}',
            inspect.stack()[0][0].f_code.co_name))
    commits = map(
        lambda x: x[2:].strip(),
        run_cmd(f'git cherry {remote_and_slash}{main_branch}',
                inspect.stack()[0][0].f_code.co_name))
    return {'filepaths': filepaths, 'commits': commits}


def analyze_changes_in_branch_diff(branch, main_branch, remote, fp):
    remote_and_slash = ''
    if remote:
        remote_and_slash = remote + '/'
    return '\n'.join(
        run_cmd(f'git diff {branch}..{remote_and_slash}{main_branch} {fp}',
                inspect.stack()[0][0].f_code.co_name))


def analyze__pushed_but_not_merged(devbranch, main_branch):
    commits = map(
        lambda x: x[2:].strip(),
        run_cmd('git cherry upstream/' + main_branch,
                inspect.stack()[0][0].f_code.co_name))

    not_pushed = analyze__in_commits_but_not_pushed(devbranch)

    unmerged_commits = [x for x in commits if x not in not_pushed['commits']]

    filepaths = []
    filepath_to_commits = {}
    for commit_id in unmerged_commits:
        filepaths_of_commit = map_paths(
            run_cmd(f'git diff-tree --no-commit-id --name-only -r {commit_id}',
                    inspect.stack()[0][0].f_code.co_name))
        filepaths.extend(filepaths_of_commit)
        for filepath in filepaths_of_commit:
            filepath_to_commits.setdefault(filepath, []).append(commit_id)

    return {
        'filepaths': filepaths,
        'commits': unmerged_commits,
        'filepath_to_commits': filepath_to_commits
    }


def analyze_changes_pushed_but_not_merged_diff(devbranch, main_branch, fp):
    status = analyze__pushed_but_not_merged(devbranch, main_branch)
    if fp.replace('../', '') in status['filepath_to_commits']:
        out = ''
        for commit in status['filepath_to_commits'][fp.replace('../', '')]:
            out = f'\nDiff of {commit}'
            out += '\n'.join(
                run_cmd(f'git show {commit} {fp}',
                        inspect.stack()[0][0].f_code.co_name))
        return out


def analyze__in_merged_prs_not_released(main_branch):
    latest_version_tag = run_cmd('git tag -l --sort -version:refname '
                                 '| grep -vE "stable|show" |head -n 1',
                                 inspect.stack()[0][0].f_code.co_name)[0]
    filepaths = map_paths(
        run_cmd(f'git diff {latest_version_tag}..upstream/{main_branch} '
                f'--name-only', inspect.stack()[0][0].f_code.co_name))
    commits = [run_cmd(f'git rev-list -n 1 upstream/{main_branch}')[0]]
    for line in run_cmd(f'git log --pretty="%H" --no-merges '
                        f'-w {latest_version_tag}..upstream/{main_branch}'):
        commits.append(line)
    return {'filepaths': filepaths, 'commits': commits,
            'latest_version_tag': latest_version_tag}


def analyze_changes_in_merged_prs_not_released_diff(main_branch, fp):
    status = analyze__in_merged_prs_not_released(main_branch)
    if fp.replace('../', '') in status['filepaths']:
        tag = status['latest_version_tag']
        return '\n'.join(
            run_cmd(f'git diff {tag}..upstream/{main_branch} {fp}',
                    inspect.stack()[0][0].f_code.co_name))


def analyze__in_recent_production_release(n):
    versions = run_cmd('git tag -l --sort -version:refname '
                       '| grep -vE "stable|show" |head -n {} '
                       '| tail -n 2'.format(n + 1),
                       inspect.stack()[0][0].f_code.co_name)
    newer = versions[0]
    older = versions[1]
    filepaths = map_paths(
        run_cmd('git diff {}..{} --name-only'.format(older, newer),
                inspect.stack()[0][0].f_code.co_name))
    commits = [run_cmd(f'git rev-list -n 1 {newer}')[0]]
    for line in run_cmd(
            f'git log --pretty="%H" --no-merges -w {older}..{newer}'):
        if line not in commits:
            commits.append(line)

    return {
        'filepaths': filepaths,
        'commits': commits,
        'version_number': newer,
        'previous_version_number': older
    }


def analyze_changes_in_recent_production_release_diff(n, fp):
    """
    fp is relative path from here.... but status['filepaths'] is absolute
    :param n:
    :param fp:
    :return:
    """
    status = analyze__in_recent_production_release(n)
    if fp.replace('../', '') in status['filepaths']:
        out = run_cmd(
            'git diff {}..{} {}'.format(status['previous_version_number'],
                                        status['version_number'],
                                        fp),
            inspect.stack()[0][0].f_code.co_name)
        return '\n'.join(out)


def compress_to_suitable_length(x):
    if len(x) > 68:
        return x[0:32] + '..' + x[-32:]
    return x


def map_paths(pathlist):
    return pathlist


def map_filepaths_to_dirpaths_if_needed(pathlist):
    files_under_dir = {}
    for path in pathlist:
        dirpath = os.path.dirname(path)
        files_under_dir.setdefault(dirpath, set()).add(path)

    mapping = {}
    for dirpath, v in files_under_dir.items():
        if len(v) > 0:
            new_path = '{}/{} files'.format(dirpath, len(v))
            for filepath in v:
                mapping[filepath] = new_path
        else:
            filepath = next(iter(v))
            mapping[filepath] = filepath

    return mapping


# noinspection PyDictCreation
def analyze_changes(main_branch, personal_branch, stage_names, commit_ids=None,
                    branch=None):
    stage_data = {}
    stage_data['unstaged'] = analyze_changes_unstaged()
    stage_data['staged'] = analyze_changes_staged()
    stage_data[
        'in_commits_but_not_pushed'] = analyze__in_commits_but_not_pushed(
        personal_branch)
    if commit_ids:
        stage_data['by_commit_ids'] = analyze__in_commits(commit_ids)
    if branch:
        stage_data['by_branch'] = analyze__in_branch(branch, main_branch,
                                                     'upstream')
    stage_data['pushed_but_not_merged'] = analyze__pushed_but_not_merged(
        personal_branch, main_branch)
    stage_data[
        'in_merged_prs_not_released'] = analyze__in_merged_prs_not_released(
        main_branch)
    stage_data['in_last_production_release'] = \
        analyze__in_recent_production_release(1)
    stage_data['in_previous_production_release'] = \
        analyze__in_recent_production_release(2)

    all_files = set()
    for k, v in stage_data.items():
        for filepath in v['filepaths']:
            all_files.add(filepath)

    map_to_dirpaths = False
    if map_to_dirpaths:
        mapping_to_dirpaths = map_filepaths_to_dirpaths_if_needed(all_files)

        for k, v in stage_data.items():
            fixed_filepaths = set()
            for filepath in v['filepaths']:
                fixed_filepaths.add(mapping_to_dirpaths[filepath])
            v['filepaths'] = list(fixed_filepaths)

    for k, v in stage_data.items():
        fixed_filepaths = []
        for filepath in v['filepaths']:
            fixed_filepaths.append(filepath)  # No changes here. earlier we
            # shortened name here
        v['filepaths'] = fixed_filepaths

    filepaths = set()
    for k, v in stage_data.items():
        for filepath in v['filepaths']:
            filepaths.add(filepath)
    filepaths = sorted(filepaths)
    return stage_names, stage_data, filepaths
