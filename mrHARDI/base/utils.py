

def if_join_str(lst, char):
    return char.join([n for n in lst if n])


def split_ext(fname):
    _lst = fname.split(".")
    return _lst[0], ".".join(_lst[1:])
