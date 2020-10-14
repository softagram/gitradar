from enum import Enum, auto

stage_names = [
    'unstaged', 'staged', 'in_commits_but_not_pushed', 'pushed_but_not_merged',
    'in_merged_prs_not_released', 'in_last_production_release',
    'in_previous_production_release'
]

stage_shortnames = {
    'unstaged': 'unstaged',
    'staged': 'staged',
    'in_commits_but_not_pushed': 'commit',
    'pushed_but_not_merged': 'review',
    'in_merged_prs_not_released': 'main',
    'in_last_production_release': 'prod',
    'in_previous_production_release': 'prod-1'
}


# TODO: use these instead of string keys for stages
class Stage(Enum):
    Unstaged = auto()
    Staged = auto()
    InCommitsButNotPushed = auto()
    PushedButNotMerged = auto()
    MergedButNotReleased = auto()
    InLastProductionRelease = auto()
    InPreviousProductionRelease = auto()
