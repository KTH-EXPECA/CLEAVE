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
from typing import Any, Callable, Dict, Type, Union

from multiprocess.context import _default_context
from multiprocess.sharedctypes import RawValue
from multiprocess.synchronize import RLock, Semaphore

from cleave.client.mproc import RunnableLoop

_ctype_mappings = {
    int  : 'q',  # signed long long
    float: 'd',  # double,
    bool : 'B'  # unsigned char
}


class RunningSensorArrayError(Exception):
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


class Sensor:
    SENSOR_VALUE = Union[int, float, bool]
    SENSOR_TYPES = Type[SENSOR_VALUE]

    def __init__(self,
                 prop_name: str,
                 prop_type: SENSOR_TYPES,
                 sampling_freq_hz: int,
                 noise_fn: Callable[[SENSOR_VALUE],
                                    SENSOR_VALUE] = lambda x: x):
        if prop_type not in _ctype_mappings:
            raise SensorTypeException('Sensors can only read integers, '
                                      'floats or booleans!')

        self._prop_name = prop_name
        self._sampl_freq = sampling_freq_hz
        self._prop_type = prop_type
        self._value = RawValue(_ctype_mappings[prop_type])
        self._noise = noise_fn

    @property
    def measured_property_name(self) -> str:
        return self._prop_name

    @property
    def sampling_frequency(self) -> int:
        return self._sampl_freq

    def write_value(self, value: Any):
        self._value.value = value

    def read_value(self) -> Any:
        return self._noise(self._prop_type(self._value.value))


class SensorArray(RunnableLoop):
    def __init__(self,
                 plant_upd_freq_hz: int):
        super(SensorArray, self).__init__()
        self._sensors = dict()
        self._cycle_triggers = dict()
        self._plant_freq = plant_upd_freq_hz
        self._cycles = -1
        self._cycle_sem = Semaphore(value=0, ctx=_default_context)
        self._sensor_lock = RLock(ctx=_default_context)

    def attach_sensor(self, sensor: Sensor):
        if not self.is_shutdown():
            raise RunningSensorArrayError()
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

    def push_samples(self, sampled_values: Dict[str, Sensor.SENSOR_VALUE]):
        if self.is_shutdown():
            return

        with self._sensor_lock:
            for prop_name, new_value in sampled_values.items():
                try:
                    self._sensors[prop_name].write_value(new_value)
                except KeyError:
                    warnings.warn(f'Ignoring received update for property'
                                  f' {prop_name} with no attached sensors.',
                                  UnassignedPropertyWarning)

            self._cycle_sem.release()

    def _loop(self) -> None:
        self._cycle_sem.acquire()
        with self._sensor_lock:
            self._cycles += 1
            # get values from sensors triggered in this cycle
            for sensor in self._cycle_triggers.get(self._cycles, []):
                value = sensor.read_value()

                # TODO do something with value
