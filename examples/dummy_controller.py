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

from cleave.api.controller import Controller
from cleave.api.util import PhyPropMapping


class DummyController(Controller):
    def process(self, sensor_values: PhyPropMapping) -> PhyPropMapping:
        # get the speed
        speed = sensor_values['speed']

        # if speed is above 15 m/s, brake
        # if below 5 m/s, accelerate
        # otherwise do nothing
        if speed > 15.0:
            accel = -1.0
        elif speed < 5.0:
            accel = 1.0
        else:
            accel = 0

        return {'accel': accel}


port = 50000
controller = DummyController()
