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
import warnings
from abc import ABC, abstractmethod
from queue import Empty
from threading import Event
from typing import Mapping, Tuple

import msgpack
import pandas as pd
from twisted.internet.posixbase import PosixReactorBase
from twisted.internet.protocol import DatagramProtocol

from .exceptions import ProtocolWarning
from .protocol import ControlMessage, ControlMessageFactory, NoMessage
from ..stats.stats import RollingStatistics
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
        self._send_stats = RollingStatistics(
            columns=['seq', 'send_time', 'size_bytes']
        )
        self._recv_stats = RollingStatistics(
            columns=['seq', 'recv_time', 'size_bytes']
        )

    def startProtocol(self):
        self._ready.set()

    def put_sensor_values(self, prop_values: Mapping[str, PhyPropType]) \
            -> None:
        # TODO: log!
        msg = self._msg_fact.create_sensor_message(prop_values)
        payload = msg.serialize()
        # this should always be called from the reactor thread
        self.transport.write(payload, self._caddr)

        # log
        self._send_stats.add_record({
            'seq'           : msg.seq,
            'send_timestamp': msg.timestamp,
            'out_size_b'    : len(payload)
        })

    def get_actuator_values(self) -> Mapping[str, PhyPropType]:
        try:
            return self._recv_q.pop_nowait()
        except Empty:
            return dict()

    def datagramReceived(self, datagram: bytes, addr: Tuple[str, int]):
        # unpack commands
        recv_time = time.time()
        try:
            msg = ControlMessage.from_bytes(datagram)
            self._recv_q.put(msg.payload)
            # log
            self._recv_stats.add_record({
                'seq'           : msg.seq,
                'recv_timestamp': recv_time,
                'in_size_b'     : len(datagram)
            })
        except NoMessage:
            pass
        except (ValueError, msgpack.FormatError, msgpack.StackError):
            warnings.warn('Could not unpack data from {}:{}.'.format(*addr),
                          ProtocolWarning)

    def register_with_reactor(self, reactor: PosixReactorBase):
        # TODO: parameterize
        def _save_stats():
            total_stats = pd.merge(
                self._send_stats.to_pandas(),
                self._recv_stats.to_pandas(),
                how='outer',  # use sequence number for both
                on='seq',
                suffixes=('_send', '_recv'),
                validate='one_to_one'
            )
            total_stats[['seq', 'out_size_b', 'in_size_b']] = \
                total_stats[['seq', 'out_size_b', 'in_size_b']].astype('int32')
            total_stats.to_csv('./udp_client_stats.csv', index=False)

        reactor.addSystemEventTrigger('before', 'shutdown', _save_stats)
        reactor.listenUDP(0, self)
