#!python
"""
Rosids - Create a Snapshot-style Backup with NTFS Hardlinks.

Status:     release-1 (2009-12-11)
Author:     LiosK <contact@mail.liosk.net>
License:    The MIT License
Copyright:  Copyright (c) 2009 LiosK.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
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
            version="release-1 (2009-12-11)",
            usage="%prog [OPTIONS] SOURCE LINK_SOURCE DESTINATION",
            description="create a snapshot-style backup with NTFS hardlinks")

    def attr_option_handler(option, opt_str, value, parser):
        if any(c not in option.metavar for c in value.upper()):
            m = "{0} option requires one or more of characters in [{1}]"
            raise optparse.OptionValueError(m.format(opt_str, option.metavar))
        else:
            setattr(parser.values, option.dest, value.upper())

    copy_group = optparse.OptionGroup(parser, "Copy Options")
    copy_group.add_option("-l", "--list-only", dest="list_only",
            action="store_true", default=False,
            help="list only - don't copy or link anything")
    copy_group.add_option("--afa", "--add-file-attr", dest="add_file_attr",
            type="string", metavar="RASHNT", default="",
            action="callback", callback=attr_option_handler,
            help="add the given attributes to copied files")
    parser.add_option_group(copy_group)

    sel_group = optparse.OptionGroup(parser, "Selection Options")
    sel_group.add_option("--xfa", "--exclude-file-by-attr",
            dest="exclude_file_by_attr", type="string", metavar="RASHCNETO",
            default="", action="callback", callback=attr_option_handler,
            help="exclude files with any of the given attributes")
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
    filter.set_exclude_file_by_attr(options.exclude_file_by_attr)
    filter.set_exclude_dir_junctions(
            options.exclude_junctions or options.exclude_dir_junctions)
    filter.set_exclude_file_junctions(
            options.exclude_junctions or options.exclude_file_junctions)
    return filter

def create_commander(src, lnk, dst, options):
    if options.list_only:
        return NullCommander()
    else:
        commander = RealCommander()
        if options.add_file_attr:
            commander.set_file_attr_to_add(options.add_file_attr)
        return commander


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
    _exclude_file_by_attr = 0
    _dir_attr_to_exclude = 0
    _file_attr_to_exclude = 0

    def set_destination(self, value):
        self._destination = os.path.normpath(value)
        return self

    def set_exclude_file_by_attr(self, value):
        self._exclude_file_by_attr = str_attrs_to_bits(value)
        return self._update_attr_to_exclude()

    def set_exclude_dir_junctions(self, value):
        self._exclude_dir_junctions = bool(value)
        return self._update_attr_to_exclude()

    def set_exclude_file_junctions(self, value):
        self._exclude_file_junctions = bool(value)
        return self._update_attr_to_exclude()

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

        if 0 < self._dir_attr_to_exclude:
            if self._has_attr(path, self._dir_attr_to_exclude):
                return True

        for pattern in self._exclude_by_regexp:
            if pattern.search(path) is not None:
                return True

        return False

    def excludes_file(self, path):
        """Return True if the file is to be excluded."""
        if 0 < self._file_attr_to_exclude:
            if self._has_attr(path, self._file_attr_to_exclude):
                return True

        for pattern in self._exclude_by_regexp:
            if pattern.search(path) is not None:
                return True

        return False

    def _has_attr(self, path, attr):
        return bool(attr & get_file_attributes(path))

    def _update_attr_to_exclude(self):
        self._dir_attr_to_exclude = 0
        if self._exclude_dir_junctions:
            self._dir_attr_to_exclude |= 0x400  # FILE_ATTRIBUTE_REPARSE_POINT
        self._file_attr_to_exclude = self._exclude_file_by_attr
        if self._exclude_file_junctions:
            self._file_attr_to_exclude |= 0x400 # FILE_ATTRIBUTE_REPARSE_POINT
        return self



class RealCommander:
    """The polymorphic proxy in charge of filesystem-changing operations."""
    _file_attr_to_add = 0

    def set_file_attr_to_add(self, value):
        self._file_attr_to_add = str_attrs_to_bits(value)
        return self

    def copy_dir(self, src, dst):
        os.mkdir(dst)
        set_file_attributes(dst, get_file_attributes(src))

    def make_dirs(self, path):
        os.makedirs(path)

    def copy_file(self, src, dst):
        if not ctypes.windll.kernel32.CopyFileW(src, dst, True):
            raise ctypes.WinError() # XXX The message is not nice.
        if 0 < self._file_attr_to_add:
            set_file_attributes(dst,
                    self._file_attr_to_add | get_file_attributes(dst))

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
        print("Link", self._get_size(path), path,
                sep="\t", file=self._out_stream)

    def log_copy(self, path):
        print("Copy", self._get_size(path), path,
                sep="\t", file=self._out_stream)

    def log_skip(self, path):
        if self._verbose:
            print("Skip", "", path, sep="\t", file=self._out_stream)

    def log_dir(self, path):
        if self._verbose:
            print("Dir.", "", path, sep="\t", file=self._out_stream)

    def error(self, path, message):
        print(path, message, sep="\t", file=self._err_stream)
        if self._verbose:
            print("Err.", "", path, sep="\t", file=self._out_stream)

    def _get_size(self, path):
        """Return the size of file, suppressing errors."""
        try:
            return os.path.getsize(path)
        except OSError:
            return -1


# utility functions
def str_attrs_to_bits(str_attrs):
    attr_map = { "R": 0x1, "H": 0x2, "S": 0x4, "A": 0x20,
            "T": 0x100, "C": 0x800, "O": 0x1000, "N": 0x2000, "E": 0x4000 }
    bits = 0
    for c in str_attrs.upper():
        if c not in attr_map:
            return -1
        else:
            bits |= attr_map[c]
    return bits

def get_file_attributes(path):
    attributes = ctypes.windll.kernel32.GetFileAttributesW(path)
    if attributes == -1:    # -1 = INVALID_FILE_ATTRIBUTES
        raise ctypes.WinError()
    else:
        return attributes

def set_file_attributes(path, attributes):
    if not ctypes.windll.kernel32.SetFileAttributesW(path, attributes):
        raise ctypes.WinError()


if __name__ == "__main__":
    main(sys.argv[1:])
