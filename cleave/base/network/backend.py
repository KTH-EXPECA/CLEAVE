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
from typing import Mapping, Tuple

import msgpack
from twisted.internet.posixbase import PosixReactorBase
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.threads import deferToThread

from .protocol import *
from ..backend.controller import Controller
from ..logging import Logger
# from ..stats.plotting import plot_controller_network_metrics
# from ..stats.stats import RollingStatistics
from ..util import PhyPropType


class UDPControllerService(DatagramProtocol):
    def __init__(self,
                 port: int,
                 controller: Controller,
                 reactor: PosixReactorBase):
        super(UDPControllerService, self).__init__()
        self._port = port
        self._controller = controller
        self._reactor = reactor
        self._msg_fact = ControlMessageFactory()
        # self._stats = RollingStatistics(
        #     columns=['seq', 'in_size_b', 'out_size_b',
        #              'recv_timestamp', 'process_time',
        #              'send_timestamp'])
        self._logger = Logger()

    def serve(self):
        # start listening
        self._logger.info('Starting controller service...')
        self._reactor.listenUDP(self._port, self)
        self._reactor.run()

    def stopProtocol(self):
        self._logger.warn('Shutting down controller service, please wait...')
        # TODO: reimplement stats and plotting
        # stats = self._stats.to_pandas()
        # # TODO: parameterize
        # self._logger.info('Writing metrics to file...')
        # stats.to_csv('udp_control_stats.csv', index=False)
        # plot_controller_network_metrics(stats, out_path='.',
        #                                 fname_prefix='udp_')
        self._logger.info('Controller service shutdown complete.')

    # def _log_input_output(self,
    #                       in_msg: ControlMessage,
    #                       in_dgram: bytes,
    #                       out_msg: ControlMessage,
    #                       out_dgram: bytes,
    #                       recv_time: float):
    #     record = {
    #         'seq'           : in_msg.seq,
    #         'in_size_b'     : len(in_dgram),
    #         'out_size_b'    : len(out_dgram),
    #         'recv_timestamp': recv_time,
    #         'process_time'  : out_msg.timestamp - recv_time,
    #         'send_timestamp': out_msg.timestamp
    #     }
    #     self._stats.add_record(record)
    # print(self._stats.rolling_window_stats(5))

    def datagramReceived(self, in_dgram: bytes, addr: Tuple[str, int]):
        # Todo: add timestamping
        # Todo: real logging
        recv_time = time.time()

        try:
            in_msg = self._msg_fact.parse_message_from_bytes(in_dgram)
            if in_msg.msg_type == ControlMsgType.SENSOR_SAMPLE:
                # TODO: use object oriented interface
                self._logger.debug(
                    'Received samples from {addr[0]}:{addr[1]}...',
                    addr=addr)

                def result_callback(act_cmds: Mapping[str, PhyPropType]) \
                        -> None:
                    # TODO: log
                    out_msg = in_msg.make_control_reply(act_cmds)
                    out_dgram = out_msg.serialize()
                    self.transport.write(out_dgram, addr)
                    self._logger.debug('Sent command to {addr[0]}:{addr[1]}.',
                                       addr=addr)

                    # TODO: reimplement
                    # log after sending
                    # deferToThread(self._log_input_output, in_msg, in_dgram,
                    #               out_msg, out_dgram, recv_time)

                d = deferToThread(self._controller.process, in_msg.payload)
                d.addCallback(result_callback)
            else:
                pass
        except NoMessage:
            pass
        except AssertionError:
            self._logger.warn(
                'Expected message with type {e_type}, instead got {act_type}!',
                e_type=ControlMsgType.SENSOR_SAMPLE.name,
                act_type=in_msg.msg_type.name
            )
        except (ValueError, msgpack.FormatError, msgpack.StackError):
            self._logger.warn(
                'Could not unpack data from {addr[0]}:{addr[1]}',
                addr=addr
            )
