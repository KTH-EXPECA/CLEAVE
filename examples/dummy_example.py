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
import time
from typing import Any, Optional

from cleave.client import BaseActuationCommand, BaseActuator, BaseSensor, \
    BaseState, Plant


class DummySensor(BaseSensor):
    def prepare_state(self, state: BaseState) -> bytes:
        return 'hello world'.encode('utf8')

    def send(self, payload: bytes) -> Any:
        return print(payload.decode('utf8'))


class DummyActuator(BaseActuator):
    def get_next_actuation(self) -> Optional[BaseActuationCommand]:
        return None

    def listen(self) -> bytes:
        time.sleep(1.0)
        return 'hello_world'.encode('utf8')

    def process_incoming(self, data: bytes):
        print(data.decode('utf8'))


class DummyState(BaseState):
    def advance(self,
                actuation: Optional[BaseActuationCommand] = None) -> BaseState:
        return self


if __name__ == '__main__':
    sensor = DummySensor(sample_freq=60)
    actuator = DummyActuator()

    state = DummyState()

    plant = Plant(
        dt=0.001,
        init_state=state,
        sensor=sensor,
        actuator=actuator
    )

    plant.run()
