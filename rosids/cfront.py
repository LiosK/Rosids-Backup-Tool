import io
import optparse
import os
import os.path
import sys

import rosids.commander
import rosids.comparator
import rosids.filter
import rosids.logger
import rosids.walker


def run(args):
    parser = _create_option_parser()
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
    walker = _create_walker(src, lnk, dst, options)
    try:
        walker.start_walk(src, lnk, dst)
    except Exception as e:
        parser.error(e)

def _create_option_parser():
    """Define command-line options, usage notes and so forth."""
    parser = optparse.OptionParser(
            version=rosids.VERSION,
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


def _create_walker(src, lnk, dst, options):
    walker = rosids.walker.Walker()
    walker.set_logger(_create_logger(src, lnk, dst, options))
    walker.set_comparator(rosids.comparator.Comparator())
    walker.set_filter(_create_filter(src, lnk, dst, options))
    walker.set_commander(_create_commander(src, lnk, dst, options))
    return walker

def _create_logger(src, lnk, dst, options):
    out_encoding = "utf-8" if options.utf8_log else sys.stdout.encoding
    out_stream = io.TextIOWrapper(sys.stdout.buffer,
            encoding=out_encoding, errors="backslashreplace", newline="")
    err_encoding = "utf-8" if options.utf8_error else sys.stdout.encoding
    err_stream = io.TextIOWrapper(sys.stderr.buffer,
            encoding=err_encoding, errors="backslashreplace", newline="")

    logger = rosids.logger.Logger()
    logger.set_out_stream(out_stream)
    logger.set_err_stream(err_stream)
    logger.set_verbose(options.verbose)
    return logger

def _create_filter(src, lnk, dst, options):
    filter = rosids.filter.Filter()
    filter.set_destination(dst)
    filter.set_exclude_by_regexp(options.exclude_by_regexp)
    filter.set_exclude_file_by_attr(options.exclude_file_by_attr)
    filter.set_exclude_dir_junctions(
            options.exclude_junctions or options.exclude_dir_junctions)
    filter.set_exclude_file_junctions(
            options.exclude_junctions or options.exclude_file_junctions)
    return filter

def _create_commander(src, lnk, dst, options):
    if options.list_only:
        return rosids.commander.NullCommander()
    else:
        commander = rosids.commander.RealCommander()
        if options.add_file_attr:
            commander.set_file_attr_to_add(options.add_file_attr)
        return commander

