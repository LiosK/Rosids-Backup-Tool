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


def main(args):
    """Application entry point."""
    parser = create_option_parser()
    (options, arguments) = parser.parse_args(args)

    # checking arguments
    if len(arguments) != 3:
        parser.error("incorrect number of arguments")
    (src, lnk, dst) = map(os.path.abspath, arguments)

    if not os.path.isdir(src):
        parser.error("SOURCE is not an existing directory")
    if not os.path.isdir(lnk):
        parser.error("LINK_SOURCE is not an existing directory")
    if os.path.isdir(dst) and len(os.listdir(dst)) > 0:
        parser.error("DESTINATION is not an empty directory")

    # executing the main process
    walker = create_walker(src, lnk, dst, options)
    try:
        walker.start_walk(src, lnk, dst)
    except Exception as e:
        parser.error(e)

def create_option_parser():
    """Define command-line options, usage notes and so forth."""
    parser = optparse.OptionParser(
            usage="%prog [OPTIONS] SOURCE LINK_SOURCE DESTINATION",
            description="create a snapshot-style backup with NTFS hardlinks")

    copy_group = optparse.OptionGroup(parser, "Copy Options")
    copy_group.add_option("-l", "--list-only", dest="list_only",
            action="store_true", default=False,
            help="list only - don't copy or link anything")
    parser.add_option_group(copy_group)

    sel_group = optparse.OptionGroup(parser, "Selection Options")
    sel_group.add_option("--xr", "--exclude-by-regexp",
            dest="exclude_by_regexp", action="append", type="string",
            metavar="PATTERN", default=[],
            help="exclude items matching regular expression PATTERN")
    sel_group.add_option("--xj", "--exclude-junctions",
            dest="exclude_junctions", action="store_true", default=False,
            help="exclude junctions (reparse points) - same as --xjd --xjf")
    sel_group.add_option("--xjd", "--exclude-dir-junctions",
            dest="exclude_dir_junctions", action="store_true", default=False,
            help="exclude junctions (reparse points) for directories")
    sel_group.add_option("--xjf", "--exclude-file-junctions",
            dest="exclude_file_junctions", action="store_true", default=False,
            help="exclude junctions (reparse points) for files")
    parser.add_option_group(sel_group)

    log_group = optparse.OptionGroup(parser, "Logging Options")
    log_group.add_option("--verbose", dest="verbose",
            action="store_true", default=False, help="enable verbose log")
    log_group.add_option("--utf8-log", dest="utf8_log", action="store_true",
            default=False, help="print log messages in UTF-8 encoding")
    log_group.add_option("--utf8-error", dest="utf8_error", action="store_true",
            default=False, help="print error messages in UTF-8 encoding")
    parser.add_option_group(log_group)

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

    logger = Logger()
    logger.set_out_stream(out_stream)
    logger.set_err_stream(err_stream)
    logger.set_verbose(options.verbose)
    return logger

def create_filter(src, lnk, dst, options):
    filter = Filter()
    filter.set_destination(dst)
    filter.set_exclude_by_regexp(options.exclude_by_regexp)
    filter.set_exclude_dir_junctions(
            options.exclude_junctions or options.exclude_dir_junctions)
    filter.set_exclude_file_junctions(
            options.exclude_junctions or options.exclude_file_junctions)
    return filter

def create_commander(src, lnk, dst, options):
    if options.list_only:
        return NullCommander()
    else:
        return RealCommander()


class Walker:
    def set_logger(self, value):
        self._logger = value
        return self

    def set_comparator(self, value):
        self._comparator = value
        return self

    def set_filter(self, value):
        self._filter = value
        return self

    def set_commander(self, value):
        self._commander = value
        return self

    def start_walk(self, src, lnk, dst):
        if self._filter.excludes_dir(src):
            self._logger.log_skip(src)
        else:
            if not os.path.isdir(dst):
                self._commander.make_dirs(dst)
            self._visit(src, lnk, dst)

    def _visit(self, src, lnk, dst):
        self._logger.log_dir(src)
        for item in os.listdir(src):
            src_item = os.path.join(src, item)
            lnk_item = os.path.join(lnk, item)
            dst_item = os.path.join(dst, item)

            try:
                if os.path.isdir(src_item):
                    if self._filter.excludes_dir(src_item):
                        self._logger.log_skip(src_item)
                    else:
                        self._commander.copy_dir(src_item, dst_item)
                        self._visit(src_item, lnk_item, dst_item)
                else:
                    if self._filter.excludes_file(src_item):
                        self._logger.log_skip(src_item)
                    else:
                        if self._comparator.is_same_file(src_item, lnk_item):
                            self._commander.link_file(lnk_item, dst_item)
                            self._logger.log_link(src_item)
                        else:
                            self._commander.copy_file(src_item, dst_item)
                            self._logger.log_copy(src_item)
            except Exception as e:
                # log and skip
                self._logger.error(src_item, e)


class Filter:
    _destination = ""
    _exclude_dir_junctions = False
    _exclude_file_junctions = False
    _exclude_by_regexp = []

    def set_destination(self, value):
        self._destination = os.path.normpath(value)
        return self

    def set_exclude_dir_junctions(self, value):
        self._exclude_dir_junctions = bool(value)
        return self

    def set_exclude_file_junctions(self, value):
        self._exclude_file_junctions = bool(value)
        return self

    def set_exclude_by_regexp(self, value):
        self._exclude_by_regexp = []
        for pattern in value:
            if pattern.startswith("(?#casesensitive)"):
                self._exclude_by_regexp.append(re.compile(pattern))
            else:
                self._exclude_by_regexp.append(re.compile(pattern, re.I))
        return self

    def excludes_dir(self, path):
        """Return True if the directory is to be excluded."""
        path = os.path.normpath(path)
        if path == self._destination:
            return True

        if self._exclude_dir_junctions and self._has_attr(path, 0x400):
            return True # 0x400 = FILE_ATTRIBUTE_REPARSE_POINT

        for pattern in self._exclude_by_regexp:
            if pattern.search(path) is not None:
                return True

        return False

    def excludes_file(self, path):
        """Return True if the file is to be excluded."""
        if self._exclude_file_junctions and self._has_attr(path, 0x400):
            return True # 0x400 = FILE_ATTRIBUTE_REPARSE_POINT

        for pattern in self._exclude_by_regexp:
            if pattern.search(path) is not None:
                return True

        return False

    def _has_attr(self, path, given_attr):
        file_attr = ctypes.windll.kernel32.GetFileAttributesW(path)
        if file_attr == -1: # -1 = INVALID_FILE_ATTRIBUTES
            raise ctypes.WinError()
        else:
            return bool(file_attr & given_attr)


class RealCommander:
    """The polymorphic proxy in charge of filesystem-changing operations."""
    def copy_dir(self, src, dst):
        os.mkdir(dst)
        attr = ctypes.windll.kernel32.GetFileAttributesW(src)
        if attr == -1:
            raise ctypes.WinError()
        elif not ctypes.windll.kernel32.SetFileAttributesW(dst, attr):
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
    _verbose = False
    _out_stream = sys.stdout
    _err_stream = sys.stderr

    def set_verbose(self, value):
        self._verbose = bool(value)
        return self

    def set_out_stream(self, value):
        self._out_stream = value
        return self

    def set_err_stream(self, value):
        self._err_stream = value
        return self

    def log_link(self, path):
        print("Link", path, sep="\t", file=self._out_stream)

    def log_copy(self, path):
        print("Copy", path, sep="\t", file=self._out_stream)

    def log_skip(self, path):
        if self._verbose:
            print("Skip", path, sep="\t", file=self._out_stream)

    def log_dir(self, path):
        if self._verbose:
            print("Dir.", path, sep="\t", file=self._out_stream)

    def error(self, path, message):
        print(path, message, sep="\t", file=self._err_stream)
        if self._verbose:
            print("Err.", path, sep="\t", file=self._out_stream)


if __name__ == "__main__":
    main(sys.argv[1:])
