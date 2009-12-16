import os
import os.path


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
