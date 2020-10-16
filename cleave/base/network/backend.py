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
import warnings
from typing import Mapping, Tuple

import msgpack
import pandas as pd
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.threads import deferToThread

from . import ProtocolWarning
from .protocol import *
from ..backend.controller import Controller
from ..stats.stats import RollingStatistics
from ..util import PhyPropType


class UDPControllerService(DatagramProtocol):
    def __init__(self, controller: Controller):
        super(UDPControllerService, self).__init__()
        self._controller = controller
        self._msg_fact = ControlMessageFactory()
        self._stats = RollingStatistics(
            columns=['seq', 'in_size_b', 'out_size_b',
                     'recv_timestamp', 'process_time',
                     'send_timestamp'])

    def get_stats(self) -> pd.DataFrame:
        return self._stats.to_pandas()

    def _log_input_output(self,
                          in_msg: ControlMessage,
                          in_dgram: bytes,
                          out_msg: ControlMessage,
                          out_dgram: bytes,
                          recv_time: float):
        record = {
            'seq'           : in_msg.seq,
            'in_size_b'     : len(in_dgram),
            'out_size_b'    : len(out_dgram),
            'recv_timestamp': recv_time,
            'process_time'  : out_msg.timestamp - recv_time,
            'send_timestamp': out_msg.timestamp
        }
        self._stats.add_record(record)
        # print(self._stats.rolling_window_stats(5))

    def datagramReceived(self, in_dgram: bytes, addr: Tuple[str, int]):
        # Todo: add timestamping
        # Todo: real logging
        recv_time = time.time()

        try:
            in_msg = self._msg_fact.parse_message_from_bytes(in_dgram)
            if in_msg.msg_type == ControlMsgType.SENSOR_SAMPLE:
                # TODO: use object oriented interface

                def result_callback(act_cmds: Mapping[str, PhyPropType]) \
                        -> None:
                    # TODO: log
                    out_msg = in_msg.make_control_reply(act_cmds)
                    out_dgram = out_msg.serialize()
                    self.transport.write(out_dgram, addr)

                    # log after sending
                    deferToThread(self._log_input_output, in_msg, in_dgram,
                                  out_msg, out_dgram, recv_time)

                d = deferToThread(self._controller.process, in_msg.payload)
                d.addCallback(result_callback)
            else:
                pass
        except NoMessage:
            pass
        except AssertionError:
            warnings.warn(f'Expected message with type '
                          f'{ControlMsgType.SENSOR_SAMPLE.name}, instead got '
                          f'{in_msg.msg_type.name}.')
        except (ValueError, msgpack.FormatError, msgpack.StackError):
            warnings.warn('Could not unpack data from {}:{}.'.format(*addr),
                          ProtocolWarning)
