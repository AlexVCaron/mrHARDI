from multiprocess.pipeline.channel import Channel


class Dataloader(Channel):
    def __init__(self, datasets, package_keys):
        super().__init__(package_keys, True)

        for dataset in datasets:
            self.add_subscriber(dataset)

    def _yield(self, sub_idx, sub):
        try:
            return super()._yield(sub_idx, sub)
        except StopIteration as e:
            self._subscribers[Channel.Sub.IN].pop(sub_idx)

        return None
