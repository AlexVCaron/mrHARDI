from collections import MutableMapping
from typing import Iterable


class ListValuedDict(MutableMapping):
    def __init__(self, init_attributes=dict()):
        self._dict = {k: self._as_list(v) for k, v in init_attributes.items()}

    def _as_list(self, item):
        if isinstance(item, list):
            return item
        if isinstance(item, Iterable):
            return list(item)

        return [item]

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

    def update(self, mapping, **kwargs):
        for k, v in mapping.items():
            self[k].extend(self._as_list(v))
