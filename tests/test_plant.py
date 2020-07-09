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
from typing import Any, Dict, Optional

from loguru import logger

from cleave.client import Plant, SimpleSensor


class DummyPlant(Plant):
    def emulation_step(self, delta_t_ns: int,
                       act_values: Optional[Dict[str, Any]] = None) \
            -> Dict[str, Any]:
        logger.info(f'Delta T: {delta_t_ns / 10e9: 0.5f} s', enqueue=True)
        logger.info(f'Plant step count: {self._step_cnt}', enqueue=True)
        return {'test_prop': 1.0}


class DummySensor(SimpleSensor):
    def __init__(self, prop: str, freq: int):
        super(DummySensor, self).__init__(prop, freq)
        self._tick_cnt = 0

    def noise(self, test: float) -> float:
        logger.info(f'Sensor tick count: {self._tick_cnt}', enqueue=True)
        self._tick_cnt += 1
        return test


if __name__ == '__main__':
    test_sensor = DummySensor('test_prop', 100)
    plant = DummyPlant(200)
    plant.register_sensor(test_sensor)

    plant.run()
