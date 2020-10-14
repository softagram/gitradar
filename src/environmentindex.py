""" Get information about the relevant changes worked on right now.
"""
import inspect
import json
import sys

from utils import run_cmd


def build__environment__version(envs, map_version_to_tag):
    environment__version = {}
    # customize this with your specific part

    try:
        from customizedenvs import build__environment__version as custom_envs
        return custom_envs(envs, map_version_to_tag)
    except ModuleNotFoundError:
        print('No customization available')
    return environment__version


def build__version__commit(environment__version):
    version__commit = {}
    for version in environment__version.values():

        for line in run_cmd(f'git rev-list -n 1 {version}',
                            inspect.stack()[0][0].f_code.co_name):
            version__commit[version] = line
            """
            TODO: a snippet for making this compatible with git tags like v1, v2 etc.
            if version.startswith('v'):
                version_without_v = version[1:]
                version__commit[version] = line
                version__commit[version_without_v] = line
            else:
                version_without_v = version
                version__commit['v' + version_without_v] = line
                version__commit[version_without_v] = line
            """
        """
        A possibly useful snippet for extending this with more fuzzy logic on versions "v1" vs. "1"
        if not version.startswith('v'):
            for line in run_cmd(f'git rev-list -n 1 v{version}',
                                inspect.stack()[0][0].f_code.co_name):
                version__commit[version] = line
                version__commit['v' + version] = line
        """
    return version__commit


def main():
    print(json.dumps(build__environment__version([sys.argv[1]], lambda y: y)))


if __name__ == '__main__':
    main()
