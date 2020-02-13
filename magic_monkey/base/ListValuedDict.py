from collections import MutableMapping


class ListValuedDict(MutableMapping):
    def __init__(self):
        self._dict = {}

    def _as_list(self, item):
        return item if type(item) is list else [item]

    def __setitem__(self, k, v):
        self._dict[k] = self._as_list(v)

    def __delitem__(self, k):
        self._dict.pop(k)

    def __getitem__(self, k):
        return self._dict[k] if k in self._dict else self._init_key(k)

    def _init_key(self, k):
        self._dict[k] = []
        return self._dict[k]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)
