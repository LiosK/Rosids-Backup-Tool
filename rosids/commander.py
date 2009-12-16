import ctypes
import os

import rosids.util


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


class RealCommander:
    """The polymorphic proxy in charge of filesystem-changing operations."""
    _file_attr_to_add = 0

    def set_file_attr_to_add(self, value):
        self._file_attr_to_add = rosids.util.str_attrs_to_bits(value)
        return self

    def copy_dir(self, src, dst):
        os.mkdir(dst)
        rosids.util.set_file_attributes(dst,
                rosids.util.get_file_attributes(src))

    def make_dirs(self, path):
        os.makedirs(path)

    def copy_file(self, src, dst):
        if not ctypes.windll.kernel32.CopyFileW(src, dst, True):
            raise ctypes.WinError() # XXX The message is not nice.
        if 0 < self._file_attr_to_add:
            rosids.util.set_file_attributes(dst, self._file_attr_to_add
                    | rosids.util.get_file_attributes(dst))

    def link_file(self, src, dst):
        if not ctypes.windll.kernel32.CreateHardLinkW(dst, src, None):
            raise ctypes.WinError() # XXX The message is not nice.
