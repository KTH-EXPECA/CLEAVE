#  Copyright (c) 2020 KTH Royal Institute of Technology
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#   limitations under the License.

from __future__ import annotations

import socket
from abc import ABC, abstractmethod
from queue import Empty
from threading import Event, Thread
from typing import Mapping, Optional

import msgpack

from ...base.util import PhyPropType, SingleElementQ

_MAX_IP_PORT = 65535
_DEFAULT_TIMEOUT_S = 0.01


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

    def __init__(self):
        self._shutdown = Event()
        self._shutdown.clear()

        self._recv_t = None
        self._send_t = None

        # We don't want a backlog, so we use custom single element queues
        self._recv_q = SingleElementQ()
        self._send_q = SingleElementQ()

    @abstractmethod
    def _send(self, payload: Mapping[str, PhyPropType]) -> None:
        pass

    @abstractmethod
    def _recv(self, timeout: Optional[float] = _DEFAULT_TIMEOUT_S) \
            -> Mapping[str, PhyPropType]:
        pass

    @abstractmethod
    def _connect_endpoints(self):
        pass

    @abstractmethod
    def _disconnect_endpoints(self):
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
                self._recv_q.put(self._recv())
            except TimeoutError:
                pass
            except IOError:
                if not self._shutdown.is_set():
                    raise

    def _send_loop(self):
        while not self._shutdown.is_set():
            try:
                self._send(self._send_q.pop(
                    timeout=_DEFAULT_TIMEOUT_S))
            except Empty:
                pass
            except IOError:
                if not self._shutdown.is_set():
                    raise

    def connect(self) -> None:
        self._connect_endpoints()

        self._recv_t = Thread(target=ThreadedCommClient._recv_loop,
                              args=(self,))
        self._send_t = Thread(target=ThreadedCommClient._send_loop,
                              args=(self,))

        # start the threads
        self._recv_t.start()
        self._send_t.start()

    def disconnect(self):
        self._disconnect_endpoints()

        self._shutdown.set()
        if self._recv_t is not None:
            self._recv_t.join()
        if self._send_t is not None:
            self._send_t.join()


class TCPCommClient(ThreadedCommClient):
    def __init__(self, host: str, port: int, max_attempts: int = 3):
        super(TCPCommClient, self).__init__()

        assert 0 <= port <= _MAX_IP_PORT  # port ranges

        self._host = host
        self._port = port
        self._max_conn_tries = max_attempts
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._unpack = msgpack.Unpacker(max_buffer_size=1024)  # TODO: magic n

    def _send(self, payload: Mapping[str, PhyPropType]) -> None:
        msgpack.pack(payload, self._sock, use_bin_type=True)

    def _recv(self, timeout: Optional[float] = _DEFAULT_TIMEOUT_S) \
            -> Mapping[str, PhyPropType]:
        # TODO: timeout?
        while True:
            buf = self._sock.recv(1024)
            if not buf:
                return {}
            self._unpack.feed(buf)
            try:
                return next(self._unpack)
            except StopIteration:
                pass

    def _connect_endpoints(self):
        tries = 1
        while True:
            try:
                self._sock.connect((self._host, self._port))
            except socket.timeout:
                if tries < self._max_conn_tries:
                    tries += 1
                else:
                    raise

    def _disconnect_endpoints(self):
        self._sock.shutdown(socket.SHUT_RDWR)
        self._sock.close()
