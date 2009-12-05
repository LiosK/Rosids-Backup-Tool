#!python
"""
Rosids - Create a Snapshot-style Backup with NTFS Hardlinks.

Author:     LiosK <contact@mail.liosk.net>
License:    The MIT License
Copyright:  Copyright (c) 2009 LiosK.
"""

import ctypes
import io
import optparse
import os
import os.path
import re
import sys


def main():
    """Application entry point."""
    parser = create_option_parser()
    (options, args) = parser.parse_args()

    # checking arguments
    if len(args) != 3:
        parser.error("Incorrect number of arguments.")
    (src, lnk, dst) = map(os.path.abspath, args)

    if not os.path.isdir(src):
        parser.error("SOURCE is not an existing directory.")
    if not os.path.isdir(lnk):
        parser.error("LINK_SOURCE is not an existing directory.")
    if os.path.isdir(dst) and len(os.listdir(dst)) > 0:
        parser.error("DESTINATION is not an empty directory.")

    # executing the main process
    walker = create_walker(src, lnk, dst, options)
    walker.start_walk(src, lnk, dst)

def create_option_parser():
    """Define command-line options, usage notes and so forth."""
    usage = "%prog [OPTIONS] SOURCE LINK_SOURCE DESTINATION"
    description = "Create a Snapshot-style Backup with NTFS Hardlinks."

    parser = optparse.OptionParser(usage=usage, description=description)

    parser.add_option("-l", "--list-only",
            dest="list_only", action="store_true", default=False)
    parser.add_option("--xj", "--exclude-junctions",
            dest="exclude_junctions", action="store_true", default=False)
    parser.add_option("--xr", "--exclude-by-regexp", dest="exclude_by_regexp",
            action="append", type="string", metavar="PATTERN", default=[])
    parser.add_option("--utf8-log",
            dest="utf8_log", action="store_true", default=False)
    parser.add_option("--utf8-error",
            dest="utf8_error", action="store_true", default=False)

    return parser

def create_walker(src, lnk, dst, options):
    walker = Walker()
    walker.set_logger(create_logger(src, lnk, dst, options))
    walker.set_comparator(Comparator())
    walker.set_filter(create_filter(src, lnk, dst, options))
    walker.set_commander(create_commander(src, lnk, dst, options))
    return walker

def create_logger(src, lnk, dst, options):
    out_encoding = "utf-8" if options.utf8_log else sys.stdout.encoding
    out_stream = io.TextIOWrapper(sys.stdout.buffer,
            encoding=out_encoding, errors="backslashreplace", newline="")
    err_encoding = "utf-8" if options.utf8_error else sys.stdout.encoding
    err_stream = io.TextIOWrapper(sys.stderr.buffer,
            encoding=err_encoding, errors="backslashreplace", newline="")
    return Logger().set_out_stream(out_stream).set_err_stream(err_stream)

def create_filter(src, lnk, dst, options):
    filter = Filter()
    filter.set_destination(dst)
    filter.set_exclude_junctions(options.exclude_junctions)
    filter.set_exclude_by_regexp(options.exclude_by_regexp)
    return filter

def create_commander(src, lnk, dst, options):
    if options.list_only:
        return NullCommander()
    else:
        return RealCommander()


class Walker:
    def set_logger(self, logger):
        self._logger = logger
        return self

    def set_comparator(self, comparator):
        self._comparator = comparator
        return self

    def set_filter(self, filter):
        self._filter = filter
        return self

    def set_commander(self, commander):
        self._commander = commander
        return self

    def start_walk(self, src, lnk, dst):
        if not self._filter.excludes_dir(src):
            if not os.path.isdir(dst):
                self._commander.make_dirs(dst)
            self._visit(src, lnk, dst)

    def _visit(self, src, lnk, dst):
        for item in os.listdir(src):
            src_item = os.path.join(src, item)
            lnk_item = os.path.join(lnk, item)
            dst_item = os.path.join(dst, item)

            if os.path.isdir(src_item):
                try:
                    if not self._filter.excludes_dir(src_item):
                        self._commander.copy_dir(src_item, dst_item)
                        self._visit(src_item, lnk_item, dst_item)
                except Exception as e:
                    # log and skip
                    self._logger.error(src_item, e)
            else:
                try:
                    if not self._filter.excludes_file(src_item):
                        if self._comparator.is_same_file(src_item, lnk_item):
                            self._commander.link_file(lnk_item, dst_item)
                            self._logger.print(src_item, 'Link')
                        else:
                            self._commander.copy_file(src_item, dst_item)
                            self._logger.print(src_item, 'Copy')

                except Exception as e:
                    # log and skip
                    self._logger.error(src_item, e)


class Filter:
    _destination = ""
    _exclude_junctions = False
    _exclude_by_regexp = []

    def set_destination(self, destination):
        self._destination = os.path.normpath(destination)
        return self

    def set_exclude_junctions(self, exclude_junctions):
        self._exclude_junctions = exclude_junctions
        return self

    def set_exclude_by_regexp(self, exclude_by_regexp):
        self._exclude_by_regexp = []
        for pattern in exclude_by_regexp:
            self._exclude_by_regexp.append(re.compile(pattern))
        return self

    def excludes_file(self, path):
        """Return True if the file is to be excluded."""
        for pattern in self._exclude_by_regexp:
            if pattern.search(path) is not None:
                return True

        return False

    def excludes_dir(self, path):
        """Return True if the directory is to be excluded."""
        path = os.path.normpath(path)
        if path == self._destination:
            return True

        if self._exclude_junctions:
            attib = ctypes.windll.kernel32.GetFileAttributesW(path)
            if attib & 0x400: # 0x400 = FILE_ATTRIBUTE_REPARSE_POINT
                return True

        for pattern in self._exclude_by_regexp:
            if pattern.search(path) is not None:
                return True

        return False


class RealCommander:
    """The polymorphic proxy in charge of filesystem-changing operations."""
    def copy_dir(self, src, dst):
        os.mkdir(dst)
        attib = ctypes.windll.kernel32.GetFileAttributesW(src)
        if attib == -1:
            raise ctypes.WinError()
        elif not ctypes.windll.kernel32.SetFileAttributesW(dst, attib):
            raise ctypes.WinError()

    def make_dirs(self, path):
        os.makedirs(path)

    def copy_file(self, src, dst):
        if not ctypes.windll.kernel32.CopyFileW(src, dst, True):
            raise ctypes.WinError() # XXX The message is not nice.


    def link_file(self, src, dst):
        if not ctypes.windll.kernel32.CreateHardLinkW(dst, src, None):
            raise ctypes.WinError() # XXX The message is not nice.


class NullCommander:
    """The empty commander used for the --list-only option."""
    def copy_dir(self, src, dst):
        pass

    def make_dirs(self, path):
        pass

    def copy_file(self, src, dst):
        pass

    def link_file(self, src, dst):
        pass


class Comparator:
    def is_same_file(self, lft, rgt):
        op = os.path
        if op.isfile(lft) and op.isfile(rgt):
            if op.getmtime(lft) == op.getmtime(rgt):
                if op.getsize(lft) == op.getsize(rgt):
                    return True

        return False


class Logger:
    _out_stream = sys.stdout
    _err_stream = sys.stderr

    def set_out_stream(self, stream):
        self._out_stream = stream
        return self

    def set_err_stream(self, stream):
        self._err_stream = stream
        return self

    def print(self, path, message):
        print(message, path, sep="\t", file=self._out_stream)

    def error(self, path, message):
        print(path, message, sep="\t", file=self._err_stream)


if __name__ == "__main__":
    main()
