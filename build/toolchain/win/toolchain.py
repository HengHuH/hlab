#!/usr/bin/env python

from __future__ import print_function
import sys


def get_toolchain_dir():
    raise NotImplementedError()


def setup_toolchain():
    raise NotImplementedError()


def main():
    pass
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
