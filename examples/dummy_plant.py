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

from cleave.api.plant import ActuatorVariable, Sensor, SensorVariable, \
    SimpleConstantActuator, State
from cleave.api.util import PhyPropType


class ExampleState(State):
    def __init__(self):
        super(ExampleState, self).__init__()

        self.accel = ActuatorVariable(0.0)
        self.speed = SensorVariable(0.0, sanity_check=lambda s: s < 200.0)
        # shuts down if speed ever exceeds 200.0 m/s

    def advance(self, dt: float) -> None:
        self.speed += dt * self.accel


class BiasSensor(Sensor):
    def __init__(self, bias: float, prop_name: str, sample_freq: int):
        super(BiasSensor, self).__init__(prop_name, sample_freq)
        self._bias = bias

    def process_sample(self, value: PhyPropType) -> PhyPropType:
        return value + self._bias


host = 'localhost'
port = 50000

tick_rate = 100
state = ExampleState()

sensors = [BiasSensor(bias=0.2, prop_name='speed', sample_freq=50)]
actuators = [SimpleConstantActuator(initial_value=0, prop_name='accel')]
