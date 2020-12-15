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

import time
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Condition
from typing import Any, Callable, Optional, Sequence, Set, Tuple, Union

import msgpack
from twisted.internet.defer import Deferred
from twisted.internet.protocol import DatagramProtocol, ProcessProtocol, \
    Protocol
from twisted.internet.threads import deferToThread
from twisted.python.failure import Failure

from .protocol import *
from ..logging import Logger
from ..recordable import CSVRecorder, NamedRecordable, Recordable, Recorder
from ...api.controller import Controller
from ...api.util import PhyPropMapping


class BusyControllerException(Exception):
    pass


class ControllerProcessingException(Exception):
    pass


# noinspection PyTypeChecker
class BaseControllerService(Recordable, ABC):
    def __init__(self,
                 controller: Controller):
        super(BaseControllerService, self).__init__()
        self._controller = controller
        self._busy_cond = Condition()
        self._busy = False
        self._logger = Logger()

    def process_sensor_samples(self,
                               samples: PhyPropMapping,
                               success_cb: Callable[[PhyPropMapping], Any]) \
            -> Deferred:
        def process() -> PhyPropMapping:
            with self._busy_cond:
                if self._busy:
                    raise BusyControllerException()
                self._busy = True

            try:
                return self._controller.process(samples)
            except Exception as e:
                raise ControllerProcessingException() from e
            finally:
                with self._busy_cond:
                    self._busy = False

        def errback(fail: Failure) -> None:
            exc = fail.trap(BusyControllerException,
                            ControllerProcessingException)

            if exc == BusyControllerException:
                self._logger.warn('Controller is busy, discarding received '
                                  'samples.')
            elif exc == ControllerProcessingException:
                self._logger.error('Error encountered while processing '
                                   'samples.')
                self._logger.error(fail.getTraceback())

        # in case the controller is busy, don't return anything
        # don't return anything if there's an error in processing either
        deferred = deferToThread(process)
        deferred.addCallback(success_cb)
        deferred.addErrback(errback)
        return deferred

    @property
    @abstractmethod
    def protocol(self) -> Union[Protocol, ProcessProtocol, DatagramProtocol]:
        pass


class UDPControllerService(BaseControllerService, DatagramProtocol):
    """
    UDP implementation of a controller service. Receives sensor samples over
    UDP and pushes them to the controller for processing.
    """

    @property
    def protocol(self) -> Union[Protocol, ProcessProtocol, DatagramProtocol]:
        return self

    def __init__(self,
                 controller: Controller,
                 output_dir: Path):
        super(UDPControllerService, self).__init__(
            controller=controller
        )
        self._out_dir = output_dir
        self._msg_fact = ControlMessageFactory()
        self._records = NamedRecordable(
            name=self.__class__.__name__,
            record_fields=['seq', 'recv_timestamp', 'recv_size',
                           'process_time', 'send_timestamp', 'send_size']

        )

        # record ourselves!
        if not self._out_dir.exists():
            self._out_dir.mkdir(parents=True, exist_ok=False)
        elif not self._out_dir.is_dir():
            raise FileExistsError(f'{self._out_dir} exists and is not a '
                                  f'directory, aborting.')

        self._recorder = CSVRecorder(self, self._out_dir, 'service')

    @property
    def recorders(self) -> Set[Recorder]:
        return self._records.recorders

    @property
    def record_fields(self) -> Sequence[str]:
        return self._records.record_fields

    def startProtocol(self) -> None:
        self._logger.info('Started controller service...')
        self._recorder.initialize()

    def stopProtocol(self) -> None:
        """
        Executed during shutdown.
        """
        self._logger.warn('Shutting down controller service.')
        self._recorder.shutdown()

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

                def result_callback(act_cmds: Optional[PhyPropMapping]) -> None:
                    if act_cmds is None:
                        return

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

                self.process_sensor_samples(in_msg.payload, result_callback)
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
