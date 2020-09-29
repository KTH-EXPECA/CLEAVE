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
import random
import socket
from typing import Mapping, Optional

import msgpack

from cleave.base.client import Actuator, SimpleSensor, builder
from cleave.base.network import ThreadedCommClient
from cleave.base.util import PhyPropType
from cleave.impl import InvPendulumState

HOST_ADDR = ('localhost', 50000)
#: Pendulum parameters
K = [-57.38901804, -36.24133932, 118.51380879, 28.97241832]
NBAR = -57.25
MAX_FORCE = 25


class CommClient(ThreadedCommClient):
    def __init__(self, host: str, port: int, max_attempts: int = 3):
        super(CommClient, self).__init__()

        assert 0 <= port <= 65535  # port ranges

        self._host = host
        self._port = port
        self._max_conn_tries = max_attempts
        # self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._unpack = msgpack.Unpacker(max_buffer_size=1024)  # TODO: magic n
        self._sock = None

    def _send(self, payload: Mapping[str, PhyPropType]) -> None:
        self._sock.sendall(msgpack.packb(payload, use_bin_type=True))

    def _recv(self, timeout: Optional[float] = 0.01) \
            -> Mapping[str, PhyPropType]:
        while True:
            buf = self._sock.recv(1024)
            if not buf:
                continue

            self._unpack.feed(buf)
            try:
                return next(self._unpack)
            except StopIteration:
                pass

    def _connect_endpoints(self):
        print(f'Trying to connect to {self._host}:{self._port}')
        self._sock = socket.create_connection((self._host, self._port))
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print('Connection success.')

    def _disconnect_endpoints(self):
        print('Client disconnecting.')
        if self._sock is not None:
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()


class NoisyActuator(Actuator):
    def __init__(self,
                 prop: str,
                 noise_pcent: float = 5,
                 noise_prob: float = 0.7):
        super(NoisyActuator, self).__init__(prop)
        self._noise_factor = noise_pcent / 100.0
        self._prob = noise_prob

    def process_actuation(self, desired_value: PhyPropType) -> PhyPropType:
        if random.random() < self._prob:
            noise = desired_value * self._noise_factor
            return desired_value + noise \
                if random.choice((True, False)) \
                else desired_value - noise
        else:
            return desired_value


if __name__ == '__main__':
    state = InvPendulumState(upd_freq_hz=200)

    builder.set_comm_handler(CommClient(*HOST_ADDR))
    builder.set_plant_state(state)
    builder.attach_sensor(SimpleSensor('position', 50))
    builder.attach_sensor(SimpleSensor('speed', 50))
    builder.attach_sensor(SimpleSensor('angle', 50))
    builder.attach_sensor(SimpleSensor('ang_vel', 50))
    builder.attach_actuator(NoisyActuator('force'))

    plant = builder.build()
    plant.execute()