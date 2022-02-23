#!/usr/bin/env python

from __future__ import print_function

import collections
import os
import sys
import platform
# import re
# import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
from gn_helpers import ToGNString


# VS versions are listed in descending order of priority (highest first).
# The first version is assumed by this script to be the one that is packaged,
# which makes a difference for the arm64 runtime.
MSVS_VERSIONS = collections.OrderedDict([
    ('2019', '16.0'),  # Default and packaged version of Visual Studio.
    ('2022', '17.0'),
    ('2017', '15.0'),
])

# # List of preferred VC toolset version based on MSVS
# # Order is not relevant for this dictionary.
# MSVC_TOOLSET_VERSION = {
#     '2022': 'VC143',
#     '2019': 'VC142',
#     '2017': 'VC141',
# }


def DetectVisualStudioPath():
    """Return path to the installed Visual Studio."""

    version_as_year = get_vs_version()

    if version_as_year >= '2022':
        program_files_path_variable = "%ProgramFiles%"
    else:
        program_files_path_variable = "%ProgramFiles(x86)%"

    for path in (
        os.environ.get('vs%s_install' % version_as_year),
        os.path.expandvars(program_files_path_variable + '/Microsoft Visual Studio/%s/Enterprise' % version_as_year),
        os.path.expandvars(program_files_path_variable + '/Microsoft Visual Studio/%s/Professional' % version_as_year),
        os.path.expandvars(program_files_path_variable + '/Microsoft Visual Studio/%s/Community' % version_as_year),
        os.path.expandvars(program_files_path_variable + '/Microsoft Visual Studio/%s/Preview' % version_as_year),
        os.path.expandvars(program_files_path_variable + '/Microsoft Visual Studio/%s/BuildTools' % version_as_year)
    ):
        # print("test path", path)
        if path and os.path.exists(path):
            return path

    raise Exception("Visual Studio Version %s not found." % version_as_year)


def NormalizePath(path):
    while path.endswith('\\'):
        path = path[:-1]
    return path


def _setup_environment():
    if sys.platform == 'win32':
        if 'GN_MSVS_OVERRIDE_PATH' not in os.environ:
            os.environ['GN_MSVS_OVERRIDE_PATH'] = DetectVisualStudioPath()


def get_runtime_dll_dirs():

    bitness = platform.architecture()[0]

    x64_path = 'System32' if bitness == '64bit' else 'Sysnative'
    x64_path = os.path.join(os.path.expandvars('%windir%'), x64_path)

    vs_runtime_dll_dirs = [x64_path, os.path.join(os.path.expandvars('%windir%'), 'SysWoW64'), 'Arm64Unused']

    return vs_runtime_dll_dirs


def get_vs_version():
    """Return best available version of Visual Studio."""
    supported_versions = list(MSVS_VERSIONS.keys())
    available_versions = []
    for version in supported_versions:

        # Detecting VS under possible paths.
        if version >= '2022':
            program_files_path_variable = '%ProgramFiles%'
        else:
            program_files_path_variable = '%ProgramFiles(x86)%'

        path = os.path.expandvars(program_files_path_variable + '/Microsoft Visual Studio/%s' % version)
        if path and any(os.path.exists(os.path.join(path, edition)) for edition in ('Enterprise', 'Professional', 'Community', 'Preview', 'BuildTools')):
            available_versions.append(version)
            break

    if not available_versions:
        supproted_versions_str = ', '.join('{} ({})'.format(v, k) for k, v in MSVS_VERSIONS.items())
        raise Exception("No supported Visual Studio can be found. Supported Versions are: %s." % supproted_versions_str)

    return available_versions[0]


def get_msvc_version():
    vs_path = os.environ['GN_MSVS_OVERRIDE_PATH']
    msvc_path = os.path.join(vs_path, "VC/Tools/MSVC")
    altenatives = []
    for d in os.listdir(msvc_path):
        if os.path.isdir(os.path.join(msvc_path, d)):
            altenatives.append(d)
    if not altenatives:
        raise Exception("No MSVC installed.")
    return max(altenatives)


def auto_detect_toolchain():
    """Gets location information about the current toolchain."""

    _setup_environment()

    runtime_dll_dirs = get_runtime_dll_dirs()

    print('''vs_path = %s
vs_version = %s
msvc_version = %s
runtime_dirs = %s
''' % (ToGNString(NormalizePath(os.environ['GN_MSVS_OVERRIDE_PATH'])),
       ToGNString(get_vs_version()), ToGNString(get_msvc_version()),
       ToGNString(os.path.pathsep.join(runtime_dll_dirs or ['None']))))


def FindFileInEnvList(env, env_name, separator, file_name, optional=False):
    parts = env[env_name].split(separator)
    for path in parts:
        if os.path.exists(os.path.join(path, file_name)):
            return os.path.realpath(path)
    assert optional, "%s is not found in %s:\n%s\nCheck if it is installed." % (
        file_name, env_name, '\n'.join(parts))
    return ''


def get_vc_bin_dir(vs_path, msvc_version, target_cpu):
    bitness = platform.architecture()[0]
    host_bit = 'Hostx64' if bitness == '64bit' else 'Hostx86'
    bin_path = os.path.join(vs_path, 'VC', 'Tools', 'MSVC', msvc_version, 'bin', host_bit, target_cpu)
    print('''vc_bin_path = %s''' % ToGNString(bin_path))


def main():
    commands = {
        "auto_detect_toolchain": auto_detect_toolchain,
        "get_vc_bin_dir": get_vc_bin_dir,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print("Expected one of : %s" % ", ".join(commands), file=sys.stderr)
        return 1

    return commands[sys.argv[1]](*sys.argv[2:])


if __name__ == '__main__':
    sys.exit(main())
