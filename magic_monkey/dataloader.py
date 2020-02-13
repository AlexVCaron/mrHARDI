from magic_monkey.base.ListValuedDict import ListValuedDict


class Dataloader:

    def __init__(self, json_data):
        self._data = ListValuedDict()
        for data in json_data:
            self._data[data["type"]].append(data)

    def get_data(self, type):
        return self._data[type]

    def load_mask(self, json_data):
        self._data["mask"] = json_data["mask"]

    def get_mask(self):
        return self._data["mask"]