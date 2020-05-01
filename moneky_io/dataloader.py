from multiprocess.pipeline.channel import Channel


class Dataloader(Channel):
    def __init__(self, datasets, package_keys):
        super().__init__(package_keys, True)

        for dataset in datasets:
            self.add_subscriber(dataset)
