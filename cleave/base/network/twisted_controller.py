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
from typing import Tuple

from twisted.internet.protocol import DatagramProtocol
from twisted.internet.threads import deferToThread
from twisted.python.failure import Failure

from ..backend.controller import Controller


class UDPControllerService(DatagramProtocol):
    def __init__(self, controller: Controller):
        super(UDPControllerService, self).__init__()
        self._controller = controller

    def datagramReceived(self, datagram: bytes, addr: Tuple[str, int]):
        # Todo: add timestamping
        # Todo: real logging

        d = deferToThread(self._controller.process_bytes, datagram)

        def result_callback(result_payload: bytes) -> None:
            self.transport.write(result_payload, addr)

        def error_callback(failure: Failure) -> None:
            failure.trap(Controller.NoSamples)

        d.addCallback(result_callback)
        d.addErrback(error_callback)
