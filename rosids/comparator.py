import os.path


class Comparator:
    def is_same_file(self, lft, rgt):
        if os.path.isfile(lft) and os.path.isfile(rgt):
            if os.path.getmtime(lft) == os.path.getmtime(rgt):
                if os.path.getsize(lft) == os.path.getsize(rgt):
                    return True

        return False
