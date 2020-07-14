from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict

from loguru import logger

from ..util import PhyPropType


class ClientCommHandler(ABC):
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
    def recv_raw_bytes(self, max_sz: int) -> bytes:
        pass

    @abstractmethod
    def send_sensor_values(self, prop_values: Dict[str, PhyPropType]):
        pass

    @abstractmethod
    def recv_actuator_values(self) -> Dict[str, PhyPropType]:
        pass


class NullClientCommHandler(ClientCommHandler):
    def __init__(self):
        super(NullClientCommHandler, self).__init__()

    def connect(self):
        logger.debug('Connecting')

    def disconnect(self):
        logger.debug('Disconnecting')

    def send_raw_bytes(self, data: bytes):
        logger.debug('Sending raw bytes: {}', data)

    def recv_raw_bytes(self, max_sz: int) -> bytes:
        logger.debug('Trying to receive {} bytes.', max_sz)
        return bytes()

    def send_sensor_values(self, prop_values: Dict[str, PhyPropType]):
        logger.debug('Sending sensors samples: {}', prop_values)

    def recv_actuator_values(self,
                             callback: Callable[[Dict[str, PhyPropType]], Any]):
        logger.debug('Listening after actuator inputs. Callback: {}',
                     callback.__name__)
