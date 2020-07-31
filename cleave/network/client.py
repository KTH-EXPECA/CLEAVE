from __future__ import annotations

from abc import ABC, abstractmethod
from queue import Empty
from threading import Event, Thread
from typing import Dict, Mapping, Optional

from ..util import PhyPropType, SingleElementQ


class CommClient(ABC):
    """
    Abstract base class for network connection clients (and other types of
    connections).
    """

    @abstractmethod
    def connect(self) -> None:
        """
        Connects this client to its associated endpoint.
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        Disconnects this client.
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


class DummyCommClient(CommClient):
    """
    Dummy implementation of a CommClient. None of its methods do anything.
    """

    def connect(self) -> None:
        pass

    def disconnect(self):
        pass

    def send_sensor_values(self, prop_values: Mapping[str, PhyPropType]):
        pass

    def recv_actuator_values(self) -> Mapping[str, PhyPropType]:
        return {}


class ThreadedCommClient(CommClient, ABC):
    """
    This class provides base abstractions for asynchronous communication
    clients such as those handling communication over sockets or between
    processes. It manages two internal threads, once for sending and one for
    receiving data.

    Extending classes need to override methods for serializing and
    deserializing data as well as methods for actually sending and receiving
    raw bytes.
    """

    DEFAULT_TIMEOUT_S = 0.01

    def __init__(self):
        self._shutdown = Event()
        self._shutdown.clear()

        self._recv_t = None
        self._send_t = None

        # We don't want a backlog, so we use custom single element queues
        self._recv_q = SingleElementQ()
        self._send_q = SingleElementQ()

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

    @abstractmethod
    def _connect(self):
        pass

    @abstractmethod
    def _disconnect(self):
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
                    timeout=ThreadedCommClient.DEFAULT_TIMEOUT_S)
            except Empty:
                continue

            payload = self._serialize(sensor_values)
            self._send_bytes(payload)

    def connect(self) -> None:
        self._recv_t = Thread(target=ThreadedCommClient._recv_loop,
                              args=(self,))
        self._send_t = Thread(target=ThreadedCommClient._send_loop,
                              args=(self,))

        # start the threads
        self._recv_t.start()
        self._send_t.start()

        self._connect()

    def disconnect(self):
        self._shutdown.set()
        if self._recv_t is not None:
            self._recv_t.join()
        if self._send_t is not None:
            self._send_t.join()

        self._disconnect()
