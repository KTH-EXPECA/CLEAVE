from abc import ABC
from typing import Any, Dict

from ..client.sensor import SensorValue


class CommHandler(ABC):
    """
    Abstraction for network connections (and other types of connections).
    """

    def connect(self):
        pass

    def disconnect(self):
        pass

    def send_raw_bytes(self, data: bytes):
        pass

    def recv_raw_bytes(self) -> bytes:
        pass

    def send_sensor_values(self, prop_values: Dict[str, SensorValue]):
        pass
