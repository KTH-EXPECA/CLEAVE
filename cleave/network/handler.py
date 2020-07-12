from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from ..util import SensorValue


class CommHandler(ABC):
    """
    Abstraction for network connections (and other types of connections).
    """

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def send_raw_bytes(self, data: bytes):
        pass

    @abstractmethod
    def recv_raw_bytes(self) -> bytes:
        pass

    @abstractmethod
    def send_sensor_values(self, prop_values: Dict[str, SensorValue]):
        pass
