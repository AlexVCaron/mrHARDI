

class Block:
    def __init__(self, sequence):
        self._sequence = sequence

    def process(self):
        for unit in self._sequence:
            unit.process()
