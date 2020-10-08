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
import warnings
from typing import Mapping, Tuple

import msgpack
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.threads import deferToThread

from . import ProtocolWarning
from .protocol import *
from ..backend.controller import Controller
from ..util import PhyPropType


class UDPControllerService(DatagramProtocol):
    def __init__(self, controller: Controller):
        super(UDPControllerService, self).__init__()
        self._controller = controller
        self._msg_fact = ControlMessageFactory()

    def datagramReceived(self, datagram: bytes, addr: Tuple[str, int]):
        # Todo: add timestamping
        # Todo: real logging

        def result_callback(act_cmds: Mapping[str, PhyPropType]) -> None:
            # TODO: log
            out_msg = self._msg_fact.create_actuation_message(act_cmds)
            self.transport.write(out_msg.serialize(), addr)

        try:
            in_msg = ControlMessage.from_bytes(datagram)
            assert in_msg.msg_type == ControlMsgType.SENSOR_SAMPLE

            # TODO: log
            # TODO: use object oriented interface
            d = deferToThread(self._controller.process, in_msg.payload)
            d.addCallback(result_callback)

        except NoMessage:
            pass
        except AssertionError:
            warnings.warn(f'Expected message with type '
                          f'{ControlMsgType.SENSOR_SAMPLE.name}, instead got '
                          f'{in_msg.msg_type.name}.')
        except (ValueError, msgpack.FormatError, msgpack.StackError):
            warnings.warn('Could not unpack data from {}:{}.'.format(*addr),
                          ProtocolWarning)
