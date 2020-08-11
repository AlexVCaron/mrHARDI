from collections import MutableMapping
from typing import Generator


class MagicDict(MutableMapping):
    def __init__(self, init_attributes=dict()):
        self._dict = init_attributes

    def __setitem__(self, k, v):
        self._dict[k] = v

    def __delitem__(self, k):
        self._dict.pop(k)

    def __getitem__(self, k):
        return self._dict[k]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def __str__(self):
        return str(self._dict)


class ListValuedDict(MagicDict):
    def __init__(self, init_attributes=dict()):
        super().__init__(
            {k: self._as_list(v) for k, v in init_attributes.items()}
        )

    def _as_list(self, item):
        if isinstance(item, list):
            return item
        if isinstance(item, Generator):
            return list(item)

        return [item]

    def __setitem__(self, k, v):
        super().__setitem__(k, self._as_list(v))

    def __getitem__(self, k):
        return super().__getitem__(k) if k in self._dict else self._init_key(k)

    def _init_key(self, k):
        self._dict[k] = []
        return self._dict[k]

    def update(self, mapping, **kwargs):
        for k, v in mapping.items():
            self[k].extend(self._as_list(v))


class Mergeable(ListValuedDict):
    def merge(self, *mergeables):
        try:
            self.update(mergeables[0])
            self.merge(*mergeables[1:])
        except StopIteration:
            pass
        except IndexError:
            pass


def key_trans(dictionary, trans):
    return dict(map(lambda k, v: (trans[k], v), *dictionary.items()))