import json
from collections.abc import MutableMapping
from copy import deepcopy
from typing import Generator

from mrHARDI.base.encoding import MagicConfigEncoder


class MagicDict(MutableMapping):
    def __init__(self, init_attributes=None, dict2arg_trans=None):
        init_attributes = self._check_initialization(init_attributes)

        self._dict = init_attributes
        self._trans = dict2arg_trans

    def _check_initialization(self, init_attributes):
        if init_attributes is None:
            init_attributes = dict()
        else:
            assert isinstance(init_attributes, dict), \
                "Base attributes of a Magic Dict " \
                "must be supplied in a dictionary"
        return init_attributes

    def copy_attributes(self):
        return deepcopy(self._dict)

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
        return str(self._attrs())

    def _attrs(self):
        if self._trans is None:
            return self._dict
        return key_trans(self._dict, self._trans)

    def __repr__(self):
        return json.dumps(self._attrs(), indent=4, cls=MagicConfigEncoder)


def _as_list(item):
    return item if isinstance(item, list) else list(item) \
                if isinstance(item, Generator) else [item]


class ListValuedDict(MagicDict):
    def __init__(self, init_attributes=None, dict2arg_trans=None):
        init_attributes = self._check_initialization(init_attributes)
        super().__init__(
            {k: _as_list(v) for k, v in init_attributes.items()},
            dict2arg_trans
        )

    def __setitem__(self, k, v):
        super().__setitem__(k, _as_list(v))

    def __getitem__(self, k):
        return super().__getitem__(k) if k in self._dict else self._init_key(k)

    def _init_key(self, k):
        self._dict[k] = []
        return self._dict[k]

    def update(self, mapping, **kwargs):
        for k, v in mapping.items():
            self[k].extend(_as_list(v))

    def _attrs(self):
        d = {
            k: (v[0] if len(v) == 1 else v) for k, v in self._dict.items()
        }
        if self._trans is None:
            return d
        return key_trans(d, self._trans)


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
    return dict(map(lambda k, v: (trans[k], v), *zip(*dictionary.items())))
