from __future__ import annotations

from abc import ABC, abstractmethod
from queue import Empty
from threading import Event, Thread
from typing import Dict, Mapping, Optional

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

    # @abstractmethod
    # def send_raw_bytes(self, data: bytes):
    #     """
    #     Directly sends a raw payload of bytes through this handler.
    #
    #     Parameters
    #     ----------
    #     data
    #         Raw payload to be sent.
    #     """
    #     pass
    #
    # @abstractmethod
    # def recv_raw_bytes(self, size: int) -> bytes:
    #     """
    #     Waits for size amount of raw bytes from the connection and returns
    #     them.
    #
    #     Parameters
    #     ----------
    #     size
    #         The number of bytes to wait for and return.
    #
    #     Returns
    #     -------
    #     bytes
    #         The received data.
    #
    #     """
    #     pass


class ThreadedClientCommHandler(ClientCommHandler, ABC):
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

    @abstractmethod
    def _serialize(self, sensor_values: Dict[str, PhyPropType]) -> bytes:
        pass

    @abstractmethod
    def _deserialize(self, payload: bytes) -> Dict[str, PhyPropType]:
        pass

    @abstractmethod
    def _send_bytes(self, payload: bytes) -> None:
        pass

    @abstractmethod
    def _recv_bytes(self,
                    timeout: Optional[float] = DEFAULT_TIMEOUT_S) -> bytes:
        pass

    def recv_actuator_values(self) -> Mapping[str, PhyPropType]:
        try:
            return self._recv_q.pop_nowait()
        except Empty:
            return dict()

    def send_sensor_values(self, prop_values: Mapping[str, PhyPropType]):
        self._send_q.put(prop_values)

    def _recv_loop(self):
        while not self._shutdown.is_set():
            try:
                payload = self._recv_bytes()
            except TimeoutError:
                continue

            act_values = self._deserialize(payload)
            self._recv_q.put(act_values)

    def _send_loop(self):
        while not self._shutdown.is_set():
            try:
                sensor_values = self._send_q.pop(
                    timeout=ThreadedClientCommHandler.DEFAULT_TIMEOUT_S)
            except Empty:
                continue

            payload = self._serialize(sensor_values)
            self._send_bytes(payload)
