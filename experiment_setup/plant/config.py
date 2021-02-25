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

_plant_n = int(os.getenv('CLEAVE_PLANT_INDEX', 0))

use_dispatcher = False
host = str(os.getenv('CLEAVE_CONTROL_HOST', '127.0.0.1'))
port = 50000 + _plant_n
tick_rate = 100
emu_duration = str(os.getenv('CLEAVE_DURATION', '35m'))
output_dir = str(os.getenv('OUTPUT_DIR', f'./plant_{_plant_n:02d}'))

state = InvPendulumState(fail_angle_rad=-1)

sample_rate = int(os.getenv('CLEAVE_SAMPLE_RATE', 100))

sensors = [
    SimpleSensor('position', sample_rate),
    SimpleSensor('speed', sample_rate),
    SimpleSensor('angle', sample_rate),
    SimpleSensor('ang_vel', sample_rate),
]

actuators = [
    SimpleConstantActuator(initial_value=0, prop_name='force')
]
