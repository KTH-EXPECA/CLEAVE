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
from ..backend.controller import Controller
from ..util import PhyPropType


class UDPControllerService(DatagramProtocol):
    def __init__(self, controller: Controller):
        super(UDPControllerService, self).__init__()
        self._controller = controller

    def datagramReceived(self, datagram: bytes, addr: Tuple[str, int]):
        # Todo: add timestamping
        # Todo: real logging

        def result_callback(act_cmds: Mapping[str, PhyPropType]) -> None:
            result_payload = msgpack.packb(act_cmds, use_bin_type=True)
            self.transport.write(result_payload, addr)

        try:
            sensor_samples = msgpack.unpackb(datagram)
            d = deferToThread(self._controller.process, sensor_samples)
            d.addCallback(result_callback)
        except (ValueError, msgpack.FormatError, msgpack.StackError):
            warnings.warn('Could not unpack data from {}:{}.'.format(*addr),
                          ProtocolWarning)
