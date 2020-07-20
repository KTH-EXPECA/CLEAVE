from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping

from ..util import PhyPropType


class ClientCommHandler(ABC):
    """
    Abstract base class for network connections (and other types of
    connections).
    """

    @abstractmethod
    def connect(self) -> None:
        """
        Connects this handler to its associated endpoint.
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        Disconnects this handler.
        """
        pass

    @abstractmethod
    def send_raw_bytes(self, data: bytes):
        """
        Directly sends a raw payload of bytes through this handler.

        Parameters
        ----------
        data
            Raw payload to be sent.
        """
        pass

    @abstractmethod
    def recv_raw_bytes(self, size: int) -> bytes:
        """
        Waits for size amount of raw bytes from the connection and returns them.

        Parameters
        ----------
        size
            The number of bytes to wait for and return.

        Returns
        -------
        bytes
            The received data.

        """
        pass

    @abstractmethod
    def send_sensor_values(self, prop_values: Mapping[str, PhyPropType]):
        """
        Send a mapping of property names to sensor values to the controller.

        Parameters
        ----------
        prop_values
            Mapping from property names to sensor values.
        """
        pass

    @abstractmethod
    def recv_actuator_values(self) -> Mapping[str, PhyPropType]:
        """
        Waits for incoming data from the controller and returns a mapping
        from actuated property names to values.

        Returns
        -------
        Mapping
            Mapping from actuated property names to values.
        """
        pass
