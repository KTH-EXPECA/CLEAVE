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
import os
from cleave.api.plant import SimpleConstantActuator, SimpleSensor
from cleave.impl.inverted_pendulum import InvPendulumState

host = os.getenv("CONTROLLER_ADDRESS")
port = os.getenv("CONTROLLER_PORT")

controller_class = 'InvPendulumController'

tick_rate = os.getenv("TIK_RATE")
emu_duration = os.getenv("EMU_DURATION")
fail_angle_rad = os.getenv("FAIL_ANGLE_RAD")

state = InvPendulumState(fail_angle_rad=int(fail_angle_rad))

sensors = [
    SimpleSensor('position', 100),
    SimpleSensor('speed', 100),
    SimpleSensor('angle', 100),
    SimpleSensor('ang_vel', 100),
]

actuators = [
    SimpleConstantActuator(initial_value=0, prop_name='force')
]

output_dir = 'plant_metrics'
