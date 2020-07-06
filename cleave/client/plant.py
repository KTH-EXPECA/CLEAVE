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
from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .mproc import TimedRunnableLoop
from .simplesensor import SimpleSensor, SensorArray


class Plant(TimedRunnableLoop, ABC):
    def __init__(self, update_freq_hz: int):
        """
        Parameters
        ----------
        update_freq_hz
            Emulation update frequency in Hertz.
        """
        super(Plant, self) \
            .__init__(dt_ns=int(math.floor((1.0 / update_freq_hz) * 10e9)))
        self._last_update = time.monotonic_ns()
        self._step_cnt = 0
        self._upd_freq = update_freq_hz

        self._sensor_array = SensorArray(self._upd_freq)

    def register_sensor(self, sensor: SimpleSensor):
        self._sensor_array.attach_sensor(sensor)

    @abstractmethod
    def emulation_step(self,
                       delta_t_ns: int,
                       act_values: Optional[Dict[str, Any]] = None) \
            -> Dict[str, Any]:
        pass

    def _loop(self) -> None:
        """
        Executes all the necessary procedures to advance the simulation a
        single discrete time step. This method calls the respective hooks,
        polls the actuator, advances the state and updates the sensor.
        """

        # TODO: pull next actuation command from actuator

        sensor_updates = \
            self.emulation_step(time.monotonic_ns() - self._last_update)
        self._last_update = time.monotonic_ns()
        self._step_cnt += 1
        self._sensor_array.push_samples(sensor_updates)

    def run(self) -> None:
        try:
            self._sensor_array.initialize()
            super(Plant, self).run()
        finally:
            self._sensor_array.shutdown()
