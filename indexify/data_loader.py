from abc import ABC, abstractmethod
from typing import List
from .data import ContentMetadata

class DataLoader(ABC):
    @abstractmethod
    def load(self, limit: int) -> List[ContentMetadata]:
        pass

    @abstractmethod
    def state(self) -> dict:
        pass
