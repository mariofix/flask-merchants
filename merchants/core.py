from abc import ABC, abstractmethod


class CoreProvider(ABC):
    name: str = "core-provider"

    @abstractmethod
    def create(self):
        raise NotImplementedError("You must implement your own create()")

    @abstractmethod
    def get(self):
        raise NotImplementedError("You must implement your own get()")

    @abstractmethod
    def refund(self):
        raise NotImplementedError("You must implement your own refund()")
