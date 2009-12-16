import os.path
import re

import rosids.util


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
        self._exclude_file_by_attr = rosids.util.str_attrs_to_bits(value)
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
        return bool(attr & rosids.util.get_file_attributes(path))

    def _update_attr_to_exclude(self):
        self._dir_attr_to_exclude = 0
        if self._exclude_dir_junctions:
            self._dir_attr_to_exclude |= 0x400  # FILE_ATTRIBUTE_REPARSE_POINT
        self._file_attr_to_exclude = self._exclude_file_by_attr
        if self._exclude_file_junctions:
            self._file_attr_to_exclude |= 0x400 # FILE_ATTRIBUTE_REPARSE_POINT
        return self
