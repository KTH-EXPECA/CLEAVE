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

import warnings
from typing import Any, Dict, Optional

from loguru import logger
from multiprocess.pool import Pool


class RunningSensorArrayError(Exception):
    pass


class StoppedSensorArrayError(Exception):
    pass


class SensorTypeException(Exception):
    pass


class FrequencyMismatchException(Exception):
    pass


class PropertyWarning(Warning):
    pass


class AssignedPropertyWarning(PropertyWarning):
    pass


class UnassignedPropertyWarning(PropertyWarning):
    pass


class SimpleSensor:
    def __init__(self,
                 prop_name: str,
                 sampling_freq_hz: int):
        self._value = None
        self._prop_name = prop_name
        self._sampl_freq = sampling_freq_hz

    @property
    def measured_property_name(self) -> str:
        return self._prop_name

    @property
    def sampling_frequency(self) -> int:
        return self._sampl_freq

    def update_value(self, value: Any):
        self._value = value

    def read_value(self) -> Any:
        return self.noise(self._value)

    @staticmethod
    def noise(raw_value: Any) -> Any:
        return raw_value


class SensorArray:
    def __init__(self,
                 plant_upd_freq_hz: int):
        super(SensorArray, self).__init__()
        self._sensors = dict()
        self._cycle_triggers = dict()
        self._plant_freq = plant_upd_freq_hz
        self._cycles = -1

        self._pool: Optional[Pool] = None

    def initialize(self):
        if self._pool is None:
            self._pool = Pool(processes=1).__enter__()

    def shutdown(self):
        if self._pool is not None:
            self._pool.close()
            self._pool.terminate()

        self._pool = None

    def attach_sensor(self, sensor: SimpleSensor):
        if self._pool is not None:
            raise RunningSensorArrayError('Cannot attach sensor to running '
                                          'array')
        elif self._plant_freq < sensor.sampling_frequency:
            raise FrequencyMismatchException('Sensor sampling frequency is '
                                             'higher than plant update '
                                             'frequency.')
        elif self._plant_freq % sensor.sampling_frequency != 0:
            raise FrequencyMismatchException('Plant frequency must be '
                                             'evenly divisible by sensor '
                                             'sampling frequency.')

        elif self._sensors.get(sensor.measured_property_name, False):
            warnings.warn('Overwriting sensor attachment for property '
                          f'{sensor.measured_property_name}',
                          AssignedPropertyWarning)

        self._sensors[sensor.measured_property_name] = sensor
        cycles_per_upd = self._plant_freq // sensor.sampling_frequency
        for c in range(0, self._plant_freq, cycles_per_upd):
            if c not in self._cycle_triggers:
                self._cycle_triggers[c] = []
            self._cycle_triggers[c].append(sensor)

    def push_samples(self, sampled_values: Dict[str, Any]):
        if self._pool is None:
            raise StoppedSensorArrayError('Cannot push samples to stopped '
                                          'sensor array!')

        logger.info('Pushing samples to sensors.')
        for prop_name, new_value in sampled_values.items():
            try:
                self._sensors[prop_name].update_value(new_value)
            except KeyError:
                warnings.warn(f'Ignoring received update for property'
                              f' {prop_name} with no attached sensors.',
                              UnassignedPropertyWarning)

        self._cycles += 1
        # get values from sensors triggered in this cycle
        for sensor in self._cycle_triggers.get(self._cycles, []):
            self._pool.apply_async(sensor.read_value)

            # TODO do something with value
            # TODO read in another process and send to controller
