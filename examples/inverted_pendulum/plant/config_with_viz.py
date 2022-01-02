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

# Example config file for an inverted pendulum inverted_pendulum

from cleave.api.plant import GaussianConstantActuator, SimpleSensor
from cleave.impl.inverted_pendulum import InvPendulumStateWithViz

host = '13.53.37.7'
port = 50001

controller_class = 'InvPendulumController'

tick_rate = 110
emu_duration = '30s'

state = InvPendulumStateWithViz(fail_angle_rad=2)

sensors = [
    SimpleSensor('position', 11),
    SimpleSensor('speed', 11),
    SimpleSensor('angle', 11),
    SimpleSensor('ang_vel', 11),
]

actuators = [
    GaussianConstantActuator('force',
                             g_mean=0.0,
                             g_std=1.0,
                             initial_value=0)
]

output_dir = '/tmp/_cleave/'
