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

import warnings
from abc import ABC, abstractmethod
from queue import Empty
from threading import Event, Thread
from typing import Mapping, Optional, Tuple

import msgpack
from twisted.internet.posixbase import PosixReactorBase
from twisted.internet.protocol import DatagramProtocol

from .exceptions import ProtocolWarning
from .protocol import ControlMessage, ControlMessageFactory, NoMessage
from ...base.util import PhyPropType, SingleElementQ

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
                self._send(self._send_q.pop(timeout=_DEFAULT_TIMEOUT_S))
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


class BaseControllerInterface(ABC):
    def __init__(self):
        self._ready = Event()
        self._ready.clear()

    @abstractmethod
    def put_sensor_values(self, prop_values: Mapping[str, PhyPropType]) \
            -> None:
        """
        Send a mapping of property names to sensor values to the controller.

        Parameters
        ----------
        prop_values
            Mapping from property names to sensor values.
        """
        pass

    @abstractmethod
    def get_actuator_values(self) -> Mapping[str, PhyPropType]:
        """
        Waits for incoming data from the controller and returns a mapping
        from actuated property names to values.

        Returns
        -------
        Mapping
            Mapping from actuated property names to values.
        """
        pass

    @abstractmethod
    def register_with_reactor(self, reactor: PosixReactorBase) -> None:
        pass

    def is_ready(self) -> bool:
        return self._ready.is_set()


class UDPControllerInterface(DatagramProtocol, BaseControllerInterface):
    def __init__(self, controller_addr: Tuple[str, int]):
        super(UDPControllerInterface, self).__init__()
        self._recv_q = SingleElementQ()
        self._caddr = controller_addr
        self._msg_fact = ControlMessageFactory()

    def startProtocol(self):
        self._ready.set()

    def put_sensor_values(self, prop_values: Mapping[str, PhyPropType]) \
            -> None:
        # TODO: log!
        msg = self._msg_fact.create_sensor_message(prop_values)
        # this should always be called from the reactor thread
        self.transport.write(msg.serialize(), self._caddr)

    def get_actuator_values(self) -> Mapping[str, PhyPropType]:
        try:
            return self._recv_q.pop_nowait()
        except Empty:
            return dict()

    def datagramReceived(self, datagram: bytes, addr: Tuple[str, int]):
        # unpack commands
        try:
            msg = ControlMessage.from_bytes(datagram)
            # TODO: log!
            self._recv_q.put(msg.payload)
        except NoMessage:
            pass
        except (ValueError, msgpack.FormatError, msgpack.StackError):
            warnings.warn('Could not unpack data from {}:{}.'.format(*addr),
                          ProtocolWarning)

    def register_with_reactor(self, reactor: PosixReactorBase):
        reactor.listenUDP(0, self)
