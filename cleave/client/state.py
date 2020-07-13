from abc import ABC, abstractmethod
from typing import Dict

from ..util import PhyPropType


class State(ABC):
    @abstractmethod
    def advance(self,
                dt_ns: int,
                act_values: Dict[str, PhyPropType]):
        pass
