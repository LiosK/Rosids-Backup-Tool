import os.path
import sys


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
