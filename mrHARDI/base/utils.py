import re


def if_join_str(lst, char):
    return char.join([n for n in lst if n])


def split_ext(fname, re_name_splitter=None):
    if re_name_splitter:
        _matches = re.findall(re_name_splitter, fname)
        if _matches:
            return _matches[1], _matches[0]
        else:
            raise ValueError("No matches found for {}".format(re_name_splitter))
    else:
        _lst = fname.split(".")
        return _lst[0], ".".join(_lst[1:])
