#!/usr/bin/env python

from __future__ import print_function

import collections
import os
import sys
import platform
import re
import subprocess

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

# List of preferred VC toolset version based on MSVS
# Order is not relevant for this dictionary.
MSVC_TOOLSET_VERSION = {
    '2022': 'VC143',
    '2019': 'VC142',
    '2017': 'VC141',
}


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

        if 'WINDOWSSDKDIR' not in os.environ:
            default_sdk_path = os.path.expandvars('%ProgramFiles(x86)%\\Windows Kits\\10')
            if os.path.isdir(default_sdk_path):
                os.environ["WINDOWSSDKDIR"] = default_sdk_path


def get_sdk_dir():
    return NormalizePath(os.environ["WINDOWSSDKDIR"])


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


def get_toolchain_dir():
    """Gets location information about the current toolchain."""

    _setup_environment()

    runtime_dll_dirs = get_runtime_dll_dirs()
    win_sdk_dir = get_sdk_dir()

    print('''vs_path = %s
sdk_path = %s
vs_version = %s
wdk_dir = %s
runtime_dirs = %s
''' % (ToGNString(NormalizePath(os.environ['GN_MSVS_OVERRIDE_PATH'])),
       ToGNString(win_sdk_dir), ToGNString(get_vs_version()),
       ToGNString(NormalizePath(os.environ.get('WDK_DIR', ''))),
       ToGNString(os.path.pathsep.join(runtime_dll_dirs or ['None']))))


def FindFileInEnvList(env, env_name, separator, file_name, optional=False):
    parts = env[env_name].split(separator)
    for path in parts:
        if os.path.exists(os.path.join(path, file_name)):
            return os.path.realpath(path)
    assert optional, "%s is not found in %s:\n%s\nCheck if it is installed." % (
        file_name, env_name, '\n'.join(parts))
    return ''


def _FormatAsEnvironmentBlock(envvar_dict):
    """Format as an 'environment block' directly suitable for CreateProcess.
    Briefly this is a list of key=value\0, terminated by an additional \0. See
    CreateProcess documentation for more details."""
    block = ''
    nul = '\0'
    for key, value in envvar_dict.items():
        block += key + '=' + value + nul
    block += nul
    return block


def _ExtractImportantEnvironment(output_of_set):
    """Extracts environment variables required for the toolchain to run from
    a textual dump output by the cmd.exe 'set' command."""
    envvars_to_save = (
        'cipd_cache_dir',  # needed by vpython
        'homedrive',  # needed by vpython
        'homepath',  # needed by vpython
        'goma_.*',  # TODO(scottmg): This is ugly, but needed for goma.
        'include',
        'lib',
        'libpath',
        'luci_context',  # needed by vpython
        'path',
        'pathext',
        'systemroot',
        'temp',
        'tmp',
        'userprofile',  # needed by vpython
        'vpython_virtualenv_root'  # needed by vpython
    )
    env = {}
    # This occasionally happens and leads to misleading SYSTEMROOT error messages
    # if not caught here.
    if output_of_set.count('=') == 0:
        raise Exception('Invalid output_of_set. Value is:\n%s' % output_of_set)
    for line in output_of_set.splitlines():
        for envvar in envvars_to_save:
            if re.match(envvar + '=', line.lower()):
                var, setting = line.split('=', 1)
                if envvar == 'path':
                    # Our own rules and actions in Chromium rely on python being in the
                    # path. Add the path to this python here so that if it's not in the
                    # path when ninja is run later, python will still be found.
                    setting = os.path.dirname(sys.executable) + os.pathsep + setting
                env[var.upper()] = setting
                break
    if sys.platform in ('win32', 'cygwin'):
        for required in ('SYSTEMROOT', 'TEMP', 'TMP'):
            if required not in env:
                raise Exception('Environment variable "%s" '
                                'required to be set to valid path' % required)
    return env


def _LoadEnvFromBat(args):
    """Given a bat command, runs it and returns env vars set by it."""
    args = args[:]
    args.extend(('&&', 'set'))
    popen = subprocess.Popen(
        args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    variables, _ = popen.communicate()
    if popen.returncode != 0:
        raise Exception('"%s" failed with error %d' % (args, popen.returncode))
    return variables.decode(errors='ignore')


def _LoadToolchainEnv(cpu, toolchain_root, sdk_dir, target_store):
    assert cpu in ('x86', 'x64', 'arm', 'arm64')

    if 'GN_MSVS_OVERRIDE_PATH' not in os.environ:
        os.environ['GN_MSVS_OVERRIDE_PATH'] = DetectVisualStudioPath()
    # We only support x64-hosted tools.
    script_path = os.path.normpath(os.path.join(os.environ['GN_MSVS_OVERRIDE_PATH'], 'VC/vcvarsall.bat'))
    if not os.path.exists(script_path):
        # vcvarsall.bat for VS 2017 fails if run after running vcvarsall.bat from
        # VS 2013 or VS 2015. Fix this by clearing the vsinstalldir environment
        # variable. Since vcvarsall.bat appends to the INCLUDE, LIB, and LIBPATH
        # environment variables we need to clear those to avoid getting double
        # entries when vcvarsall.bat has been run before gn gen. vcvarsall.bat
        # also adds to PATH, but there is no clean way of clearing that and it
        # doesn't seem to cause problems.
        if 'VSINSTALLDIR' in os.environ:
            del os.environ['VSINSTALLDIR']
            if 'INCLUDE' in os.environ:
                del os.environ['INCLUDE']
            if 'LIB' in os.environ:
                del os.environ['LIB']
            if 'LIBPATH' in os.environ:
                del os.environ['LIBPATH']
        other_path = os.path.normpath(os.path.join(
            os.environ['GN_MSVS_OVERRIDE_PATH'], 'VC/Auxiliary/Build/vcvarsall.bat'))
        if not os.path.exists(other_path):
            raise Exception('%s is missing - make sure VC++ tools are installed.' %
                            script_path)
        script_path = other_path
    cpu_arg = "amd64"
    if (cpu != 'x64'):
        # x64 is default target CPU thus any other CPU requires a target set
        cpu_arg += '_' + cpu
    args = [script_path, cpu_arg, ]
    # Store target must come before any SDK version declaration
    if (target_store):
        args.append('store')
    # Explicitly specifying the SDK version to build with to avoid accidentally
    # building with a new and untested SDK. This should stay in sync with the
    # packaged toolchain in build/vs_toolchain.py.
    args.append('10.0.19041.0')
    variables = _LoadEnvFromBat(args)

    return _ExtractImportantEnvironment(variables)


def setup_toolchain(vs_path, sdk_path, runtime_dirs, target_os, target_cpu, env_name):
    if env_name == 'none':
        env_name = ''

    if (target_os == 'winuwp'):
        target_store = True
    else:
        target_store = False

    cpus = ('x86', 'x64', 'arm', 'arm64')
    assert target_cpu in cpus
    vc_bin_dir = ''
    vc_lib_path = ''
    vc_lib_atlmfc_path = ''
    vc_lib_um_path = ''

    include = ''
    lib = ''

    def relflag(s):  # Make s relative to builddir when cwd and sdk on same drive.
        try:
            return os.path.relpath(s).replace('\\', '/')
        except ValueError:
            return s

    def q(s):  # Quote s if it contains spaces or other weird characters.
        return s if re.match(r'^[a-zA-Z0-9._/\\:-]*$', s) else '"' + s + '"'

    for cpu in cpus:
        if cpu == target_cpu:
            env = _LoadToolchainEnv(cpu, vs_path, sdk_path, target_store)
            env['PATH'] = runtime_dirs + os.pathsep + env['PATH']

            vc_bin_dir = FindFileInEnvList(env, 'PATH', os.pathsep, 'cl.exe')
            vc_lib_path = FindFileInEnvList(env, 'LIB', ';', 'msvcrt.lib')
            vc_lib_atlmfc_path = FindFileInEnvList(env, 'LIB', ';', 'atls.lib', optional=True)
            vc_lib_um_path = FindFileInEnvList(env, 'LIB', ';', 'user32.lib')

            include = [p.replace('"', r'\"') for p in env['INCLUDE'].split(';') if p]
            include = list(map(relflag, include))

            lib = [p.replace('"', r'\"') for p in env['LIB'].split(';') if p]
            lib = list(map(relflag, lib))

            include_I = ' '.join([q('/I' + i) for i in include])
            include_imsvc = ' '.join([q('-imsvc' + i) for i in include])
            libpath_flags = ' '.join([q('-libpath:' + i) for i in lib])

            if (env_name != ''):
                env_block = _FormatAsEnvironmentBlock(env)
                with open(env_name, 'w') as f:
                    f.write(env_block)

    print('vc_bin_dir = ' + ToGNString(vc_bin_dir))
    assert include_I
    print('include_flags_I = ' + ToGNString(include_I))
    assert include_imsvc
    if bool(int(os.environ.get('DEPOT_TOOLS_WIN_TOOLCHAIN', 1))) and sdk_path:
        print('include_flags_imsvc = ' + ToGNString(q('/winsysroot' + relflag(vs_path))))
    else:
        print('include_flags_imsvc = ' + ToGNString(include_imsvc))
    print('vc_lib_path = ' + ToGNString(vc_lib_path))
    if (vc_lib_atlmfc_path != ''):
        print('vc_lib_atlmfc_path = ' + ToGNString(vc_lib_atlmfc_path))
    print('vc_lib_um_path = ' + ToGNString(vc_lib_um_path))
    print('paths = ' + ToGNString(env['PATH']))
    assert libpath_flags
    print('libpath_flags = ' + ToGNString(libpath_flags))


def main():
    commands = {
        "get_toolchain_dir": get_toolchain_dir,
        "setup_toolchain": setup_toolchain
    }

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print("Expected one of : %s" % ", ".join(commands), file=sys.stderr)
        return 1

    return commands[sys.argv[1]](*sys.argv[2:])


if __name__ == '__main__':
    sys.exit(main())
