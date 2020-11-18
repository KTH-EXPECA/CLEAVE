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
#  limitations under the License.
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
#  limitations under the License.
import time
from typing import Sequence, Set, Tuple

import msgpack
from twisted.internet.posixbase import PosixReactorBase
from twisted.internet.protocol import DatagramProtocol

from .protocol import *
from ...api.controller import Controller
from ..backend.controller import ControllerWrapper
from ..logging import Logger
from ..recordable import NamedRecordable, Recordable, Recorder
from ...api.util import PhyPropMapping


class UDPControllerService(Recordable, DatagramProtocol):
    """
    UDP implementation of a controller service. Receives sensor samples over
    UDP and pushes them to the controller for processing.
    """

    def __init__(self,
                 port: int,
                 controller: Controller,
                 reactor: PosixReactorBase):
        super(UDPControllerService, self).__init__()
        self._port = port
        self._control = ControllerWrapper(controller, reactor)
        self._reactor = reactor
        self._msg_fact = ControlMessageFactory()
        self._logger = Logger()

        self._records = NamedRecordable(
            name=self.__class__.__name__,
            record_fields=['seq', 'recv_timestamp', 'recv_size',
                           'process_time', 'send_timestamp', 'send_size']

        )

    @property
    def recorders(self) -> Set[Recorder]:
        return self._records.recorders

    @property
    def record_fields(self) -> Sequence[str]:
        return self._records.record_fields

    def serve(self) -> None:
        """
        Starts listening for and serving control requests.
        """

        # start listening
        self._logger.info('Starting controller service...')
        self._reactor.listenUDP(self._port, self)
        self._reactor.run()

    def stopProtocol(self) -> None:
        """
        Executed during shutdown.
        """
        self._logger.warn('Shutting down controller service.')

    def datagramReceived(self, in_dgram: bytes, addr: Tuple[str, int]):
        """
        Executed on each datagram received.
        """

        # Todo: add timestamping
        # Todo: real logging
        # TODO: figure out way of measuring number of discarded inputs (ie
        #  that come in while the controller is busy)
        recv_time = time.time()
        in_size = len(in_dgram)
        self._logger.debug('Received {b} bytes from {addr[0]}:{addr[1]}...',
                           b=in_size, addr=addr)

        try:
            in_msg = self._msg_fact.parse_message_from_bytes(in_dgram)
            if in_msg.msg_type == ControlMsgType.SENSOR_SAMPLE:
                self._logger.info('Got control request.')

                def result_callback(act_cmds: PhyPropMapping) -> None:
                    out_msg = in_msg.make_control_reply(act_cmds)
                    out_dgram = out_msg.serialize()
                    out_size = len(out_dgram)
                    self.transport.write(out_dgram, addr)
                    self._logger.debug(
                        'Sent command to {addr[0]}:{addr[1]} ({b} bytes).',
                        addr=addr, b=out_size)

                    self._records.push_record(
                        seq=in_msg.seq,
                        recv_timestamp=recv_time,
                        recv_size=in_size,
                        process_time=out_msg.timestamp - recv_time,
                        send_timestamp=out_msg.timestamp,
                        send_size=out_size
                    )

                self._control.process_sensor_samples(in_msg.payload,
                                                     result_callback)
            else:
                self._logger.warn(f'Ignoring message of unrecognized type '
                                  f'{in_msg.msg_type.name}.')
        except NoMessage:
            pass
        except (ValueError, msgpack.FormatError, msgpack.StackError):
            self._logger.warn(
                'Could not unpack data from {addr[0]}:{addr[1]}',
                addr=addr
            )
