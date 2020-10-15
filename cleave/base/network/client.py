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
from threading import Event
from typing import Mapping, Tuple

import msgpack
from twisted.internet.posixbase import PosixReactorBase
from twisted.internet.protocol import DatagramProtocol

from .exceptions import ProtocolWarning
from .protocol import ControlMessage, ControlMessageFactory, NoMessage
from ...base.util import PhyPropType, SingleElementQ


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
