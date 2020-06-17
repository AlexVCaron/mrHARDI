from multiprocess.comm.channel import Channel


class Dataloader(Channel):
    def __init__(self, main_loop, datasets, package_keys):
        super().__init__(main_loop, package_keys, True, name="dataloader")

        for dataset in datasets:
            self.add_subscriber(dataset)

    def _looping_required(self, end_cnd):
        end_val = end_cnd()
        return not end_val and self.has_inputs()
