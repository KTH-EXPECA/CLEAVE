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
#   limitations under the License.
from typing import Dict

from cleave.client import SimpleActuator, SimpleSensor, State, builder
from cleave.util import PhyPropType


class DummyState(State):
    def __init__(self):
        self._temp = 0

    def advance(self, dt_ns: int, act_values: Dict[str, PhyPropType]) \
            -> Dict[str, PhyPropType]:
        self._temp += 1
        return {'temperature': self._temp}


if __name__ == '__main__':
    builder.reset()
    builder.set_plant_state(DummyState())
    builder.set_comm_handler(None)  # TODO client comm handler
    builder.attach_sensor(SimpleSensor('temperature', 100))
    builder.attach_sensor(SimpleActuator('cooling'))
    plant = builder.build(plant_upd_freq=200)

    plant.execute()
