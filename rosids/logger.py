import os.path
import sys


class Logger:
    _verbose = False
    _log_writer = sys.stdout
    _err_writer = sys.stderr

    def set_verbose(self, value):
        self._verbose = bool(value)
        return self

    def set_log_writer(self, value):
        self._log_writer = value
        return self

    def set_err_writer(self, value):
        self._err_writer = value
        return self

    def log_link(self, path):
        print("Link", self._get_size(path), path,
                sep="\t", file=self._log_writer)

    def log_copy(self, path):
        print("Copy", self._get_size(path), path,
                sep="\t", file=self._log_writer)

    def log_skip(self, path):
        if self._verbose:
            print("Skip", "", path, sep="\t", file=self._log_writer)

    def log_dir(self, path):
        if self._verbose:
            print("Dir.", "", path, sep="\t", file=self._log_writer)

    def error(self, path, message):
        print(path, message, sep="\t", file=self._err_writer)
        if self._verbose:
            print("Err.", "", path, sep="\t", file=self._log_writer)

    def _get_size(self, path):
        """Return the size of file, suppressing errors."""
        try:
            return os.path.getsize(path)
        except OSError:
            return -1
