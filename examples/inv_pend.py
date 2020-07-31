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

from cleave.client.base import builder
from cleave.client.impl import InvPendulumState
from cleave.network.client import DummyCommClient

if __name__ == '__main__':
    state = InvPendulumState()

    builder.set_comm_handler(DummyCommClient())
    builder.set_plant_state(state)

    plant = builder.build(plant_upd_freq=60)
    plant.execute()
