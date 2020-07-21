from __future__ import annotations

from abc import ABC, abstractmethod
from threading import Event, Thread
from typing import Mapping

from ..util import PhyPropType, SingleElementQ


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


class ThreadedClientCommHandler(ABC, ClientCommHandler):
    DEFAULT_TIMEOUT_S = 0.01

    def __init__(self):
        self._shutdown = Event()
        self._shutdown.clear()

        self._recv_t = Thread(target=ThreadedClientCommHandler._recv_loop,
                              args=(self,))
        self._send_t = Thread(target=ThreadedClientCommHandler._send_loop,
                              args=(self,))

        # We don't want a backlog, so we use custom single element queues
        self._recv_q = SingleElementQ()
        self._send_q = SingleElementQ()

        # start the threads
        self._recv_t.start()
        self._send_t.start()

    def _recv_loop(self):
        pass

    def _send_loop(self):
        while not self._shutdown.is_set():
            try:
                payload = self._send_q.pop(
                    timeout=ThreadedClientCommHandler.DEFAULT_TIMEOUT_S)
            except TimeoutError:
                continue
