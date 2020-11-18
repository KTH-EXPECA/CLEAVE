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

import time
from abc import ABC, abstractmethod
from queue import Empty
from threading import Event
from typing import Mapping, Sequence, Set, Tuple

import msgpack
import numpy as np
from twisted.internet.posixbase import PosixReactorBase
from twisted.internet.protocol import DatagramProtocol

from .protocol import ControlMessageFactory, NoMessage
from ..logging import Logger
from ..recordable import NamedRecordable, Recordable, Recorder
from ...core.util import SingleElementQ
from ...api.util import PhyPropMapping


class BaseControllerInterface(Recordable, ABC):
    """
    Defines the core interface for interacting with controllers.
    """

    def __init__(self):
        self._ready = Event()
        self._ready.clear()
        self._log = Logger()

    @abstractmethod
    def put_sensor_values(self, prop_values: PhyPropMapping) -> None:
        """
        Send a sample of sensor values to the controller.

        Parameters
        ----------
        prop_values
            Mapping from property names to sensor values.
        """
        pass

    @abstractmethod
    def get_actuator_values(self) -> PhyPropMapping:
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
        """
        Registers this ControllerInterface with the event loop reactor.
        Parameters
        ----------
        reactor
        """
        pass

    def is_ready(self) -> bool:
        return self._ready.is_set()


class UDPControllerInterface(DatagramProtocol, BaseControllerInterface):
    """
    Controller interface which abstracts over-the-network interaction with a
    controller over UDP.
    """

    def __init__(self, controller_addr: Tuple[str, int]):
        super(UDPControllerInterface, self).__init__()
        self._recv_q = SingleElementQ()
        self._caddr = controller_addr
        self._msg_fact = ControlMessageFactory()
        self._waiting_for_reply = {}

        self._records = NamedRecordable(
            name=self.__class__.__name__,
            record_fields=['seq', 'send_timestamp', 'send_size'],
            opt_record_fields={'recv_timestamp': np.nan,
                               'recv_size'     : np.nan,
                               'rtt'           : np.inf}
        )

    @property
    def recorders(self) -> Set[Recorder]:
        return self._records.recorders

    @property
    def record_fields(self) -> Sequence[str]:
        return self._records.record_fields

    def startProtocol(self):
        self._ready.set()

    def stopProtocol(self):
        self._log.info('Recording messages which never got a reply...')
        for _, out in self._waiting_for_reply.items():
            self._records.push_record(
                seq=out['msg'].seq,
                send_timestamp=out['msg'].timestamp,
                send_size=out['size']
            )

    def put_sensor_values(self, prop_values: PhyPropMapping) -> None:
        msg = self._msg_fact.create_sensor_message(prop_values)
        payload = msg.serialize()
        # this should always be called from the reactor thread
        self.transport.write(payload, self._caddr)
        self._waiting_for_reply[msg.seq] = {'msg' : msg,
                                            'size': len(payload)}

    def get_actuator_values(self) -> PhyPropMapping:
        try:
            return self._recv_q.pop_nowait()
        except Empty:
            return dict()

    def datagramReceived(self, datagram: bytes, addr: Tuple[str, int]):
        # unpack commands
        recv_time = time.time()
        try:
            msg = self._msg_fact.parse_message_from_bytes(datagram)
            out = self._waiting_for_reply.pop(msg.seq)

            self._records.push_record(
                seq=out['msg'].seq,
                send_timestamp=out['msg'].timestamp,
                send_size=out['size'],
                recv_timestamp=recv_time,
                recv_size=len(datagram),
                rtt=recv_time - out['msg'].timestamp
            )

            self._recv_q.put(msg.payload)
        except NoMessage:
            pass
        except KeyError:
            self._log.warn('Ignoring unprompted controller command.')
        except (ValueError, msgpack.FormatError, msgpack.StackError):
            self._log.warn('Could not unpack data from {}:{}.'.format(*addr))

    def register_with_reactor(self, reactor: PosixReactorBase):
        reactor.listenUDP(0, self)
