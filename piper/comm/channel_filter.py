

class ChannelFilter:
    def __init__(self, filtered_item, includes=None, excludes=None):
        self.item = filtered_item
        self.includes = includes
        self.excludes = excludes

    def get_filter_on_item(self):
        return self.item, self.includes, self.excludes
