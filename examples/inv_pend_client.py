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
import site

# extend path to find cleave package from inside the examples directory
site.addsitedir('../cleave')

from cleave.base.client import Actuator, SimpleActuator, SimpleSensor, builder
from cleave.base.network.client import UDPControllerInterface
from cleave.base.util import PhyPropType
from cleave.impl.inverted_pendulum import InvPendulumStateNoPyglet

HOST_ADDR = ('127.0.0.1', 50000)
#: Pendulum parameters
K = [-57.38901804, -36.24133932, 118.51380879, 28.97241832]
NBAR = -57.25
MAX_FORCE = 25


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
    state = InvPendulumStateNoPyglet(upd_freq_hz=200)

    builder.set_controller(UDPControllerInterface(HOST_ADDR))
    builder.set_plant_state(state)
    builder.attach_sensor(SimpleSensor('position', 100))
    builder.attach_sensor(SimpleSensor('speed', 100))
    builder.attach_sensor(SimpleSensor('angle', 100))
    builder.attach_sensor(SimpleSensor('ang_vel', 100))
    builder.attach_actuator(SimpleActuator('force'))

    plant = builder.build(plotting=True)
    plant.execute()
