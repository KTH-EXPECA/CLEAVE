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
import signal
import sys


def _handler(*args, **kwargs):
    print(f'got {args}, {kwargs}')
    exit(0)


from cleave.base.eventloop import reactor
from cleave.base.network.backend import UDPControllerService
from cleave.impl import InvPendulumController

if __name__ == '__main__':
    _, port, *_ = sys.argv
    port = int(port)
    controller = InvPendulumController(ref=0.2)
    service = UDPControllerService(controller)

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)

    # callback for shutdown
    reactor.addSystemEventTrigger('before', 'shutdown',
                                  lambda: service.get_stats()
                                  .to_csv('./stats.csv', index=False))

    reactor.listenUDP(port, service)
    reactor.run()
