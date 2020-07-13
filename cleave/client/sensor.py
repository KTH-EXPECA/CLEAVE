from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from threading import RLock
from typing import Dict

from ..network import ClientCommHandler
from ..util import IncompatibleFrequenciesError, MissingPropertyError, \
    RegisteredSensorWarning, PhyPropType


class Sensor(ABC):
    def __init__(self, prop_name: str, fs: int):
        self._prop_name = prop_name
        self._sample_freq = fs
        self._value = None

    @property
    def measured_property_name(self) -> str:
        return self._prop_name

    @property
    def sampling_frequency(self) -> int:
        return self._sample_freq

    @abstractmethod
    def process_sample(self, value: PhyPropType) -> PhyPropType:
        pass


class SimpleSensor(Sensor):
    def process_sample(self, value: PhyPropType) -> PhyPropType:
        return value


class SensorArray:
    def __init__(self, plant_freq: int, comm: ClientCommHandler):
        super(SensorArray, self).__init__()
        self._plant_freq = plant_freq
        self._prop_sensors = dict()
        self._cycle_triggers = dict()
        self._cycle_count = 0
        self._lock = RLock()
        self._comm = comm

    def _recalculate_cycle_triggers(self):
        """
        Internal helper method to recalculate cycle triggers

        Example: if a 200 Hz sensor is attached to a plant which updates at
        600 Hz, that means that for each sensor cycle, 3 plant cycles need to
        have passed. So, using the plant cycle count as reference, the sensor
        needs to sample at cycles:
        [0, 3, 6, 8, 12, ..., 600]
        """

        with self._lock:
            self._cycle_triggers = dict()
            for _, sensor in self._prop_sensors.items():
                pcycles_per_scycle = \
                    self._plant_freq // sensor.sampling_frequency
                for trigger in range(0, self._plant_freq, pcycles_per_scycle):
                    if trigger not in self._cycle_triggers:
                        self._cycle_triggers[trigger] = []

                    self._cycle_triggers[trigger].append(sensor)

    def add_sensor(self, sensor: Sensor):
        with self._lock:
            if sensor.measured_property_name in self._prop_sensors:
                warnings.warn(f'Replacing already registered sensor for '
                              f'property {sensor.measured_property_name}',
                              RegisteredSensorWarning)
            elif sensor.sampling_frequency > self._plant_freq:
                raise IncompatibleFrequenciesError(
                    'Sensor sampling frequency cannot be higher than plant '
                    'update frequency!'
                )
            elif self._plant_freq % sensor.sampling_frequency != 0:
                raise IncompatibleFrequenciesError(
                    'Sensor sampling frequency must be a divisor of plant '
                    'sampling frequency!'
                )

            self._prop_sensors[sensor.measured_property_name] = sensor
            self._recalculate_cycle_triggers()

    def update_property_values(self, prop_values: Dict[str, PhyPropType]):
        with self._lock:
            try:
                # check which sensors need to be updated this cycle
                processed_values = dict()
                for sensor in self._cycle_triggers[self._cycle_count]:
                    try:
                        prop_name = sensor.measured_property_name
                        value = prop_values[prop_name]
                        processed_value = sensor.process_sample(value)
                        processed_values[prop_name] = processed_value
                    except KeyError:
                        raise MissingPropertyError(
                            'Missing expected update for property '
                            f'{sensor.measured_property_name}!')

                # send updated values (if any) to commhandler
                if len(processed_values) > 0:
                    self._comm.send_sensor_values(processed_values)
            except KeyError:
                # no sensors on this cycle
                pass
            finally:
                self._cycle_count = (self._cycle_count + 1) % self._plant_freq
