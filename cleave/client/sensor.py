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

from multiprocessing.synchronize import SemLock
from typing import Any, Callable, List, Type, Union

from multiprocess.context import _default_context
from multiprocess.sharedctypes import RawValue
from multiprocess.synchronize import Semaphore

from cleave.client.mproc import RunnableLoop

_ctype_mappings = {
    int  : 'q',  # signed long long
    float: 'd',  # double,
    bool : 'B'  # unsigned char
}


class SensorTypeException(Exception):
    pass


class FrequencyMismatchException(Exception):
    pass


class Sensor:
    SENSOR_TYPES = Type[Union[int, float, bool]]

    def __init__(self,
                 prop_name: str,
                 prop_type: SENSOR_TYPES,
                 sampling_freq_hz: int,
                 noise_fn: Callable[[SENSOR_TYPES],
                                    SENSOR_TYPES] = lambda x: x):
        if prop_type not in _ctype_mappings:
            raise SensorTypeException('Sensors can only read integers, '
                                      'floats or booleans!')

        self._prop_name = prop_name
        self._sampl_freq = sampling_freq_hz
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
        return self._noise(self._value.value)


class SensorLoop(RunnableLoop):
    def __init__(self,
                 plant_upd_freq_hz: int,
                 sensors: List[Sensor],
                 shared_lock: SemLock):
        super(SensorLoop, self).__init__()
        self._cycle_triggers = dict()
        for sensor in sensors:
            cycles_per_upd = plant_upd_freq_hz // sensor.sampling_frequency
            for c in range(0, plant_upd_freq_hz, cycles_per_upd):
                if c not in self._cycle_triggers:
                    self._cycle_triggers[c] = []
                self._cycle_triggers[c].append(sensor)

        self._plant_freq = plant_upd_freq_hz
        self._cycles = -1
        self._cycle_sem = Semaphore(value=0, ctx=_default_context)
        self._lock = shared_lock

    def tick(self):
        self._cycle_sem.release()

    def _loop(self) -> None:
        self._cycle_sem.acquire()
        with self._lock:
            self._cycles += 1
            # get values from sensors triggered in this cycle
            for sensor in self._cycle_triggers.get(self._cycles, []):
                value = sensor.read_value()

                # TODO do something with value
