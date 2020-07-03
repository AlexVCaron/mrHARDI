from abc import ABC, abstractmethod
from uuid import uuid4


class Serializable(ABC):
    def __init__(self):
        self._uuid = uuid4()

    @property
    @abstractmethod
    def serialize(self):
        return {
            'uuid': self._uuid,
            'type': type(self)
        }
