import ctypes


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
