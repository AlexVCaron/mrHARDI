from asyncio.futures import Future


class CloseCondition(Future):
    def __init__(self):
        super().__init__()
        self._set = False

    def set(self):
        self._set = True
        self.set_result(self._set)

    def __bool__(self):
        return self._set