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

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import Collection, Dict, Mapping, Sequence, Set

import numpy as np

from cleave.core.recordable import NamedRecordable, Recordable, Recorder
from ...core.util import PhyPropMapping, PhyPropType

__all__ = ['Sensor', 'SimpleSensor', 'SensorArray',
           'NoSensorUpdate', 'RegisteredSensorWarning',
           'IncompatibleFrequenciesError', 'MissingPropertyError']


class RegisteredSensorWarning(Warning):
    pass


class IncompatibleFrequenciesError(Exception):
    pass


class MissingPropertyError(Exception):
    pass


class NoSensorUpdate(Exception):
    pass


class Sensor(ABC):
    """
    Abstract core class for sensors. Implementations should override the
    process_sample() method with their logic.
    """

    def __init__(self, prop_name: str, fs: int):
        self._prop_name = prop_name
        self._sample_freq = fs
        self._value = None

    @property
    def measured_property_name(self) -> str:
        """

        Returns
        -------
        str
            Name of the property monitored by this sensor.

        """
        return self._prop_name

    @property
    def sampling_frequency(self) -> int:
        """

        Returns
        -------
        int
            Sampling frequency of this sensor, expressed in Hertz.

        """
        return self._sample_freq

    @abstractmethod
    def process_sample(self, value: PhyPropType) -> PhyPropType:
        """
        Processes the measured value. This method should be implemented by
        subclasses to include sensor-specific behaviors.

        Parameters
        ----------
        value
            The latest measurement of the monitored property.

        Returns
        -------
        PhyPropType
            A possibly transformed value of the monitored property, according to
            the internal parameters of this sensor.

        """
        pass


class SimpleSensor(Sensor):
    """
    Simplest implementation of a sensor, which performs no processing on the
    read value and returns it as-is.
    """

    def process_sample(self, value: PhyPropType) -> PhyPropType:
        return value


class SensorArray(Recordable):
    """
    Internal utility class to manage a collection of Sensors attached to a
    Plant.
    """

    def __init__(self,
                 plant_freq: int,
                 sensors: Collection[Sensor]):
        super(SensorArray, self).__init__()
        self._plant_freq = plant_freq
        self._prop_sensors = dict()
        self._cycle_triggers = dict()

        # TODO: add clock?

        # assign sensors to properties
        for sensor in sensors:
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

            # calculate cycle triggers
            # Example: if a 200 Hz sensor is attached to a plant which
            # updates at 600 Hz, that means that for each sensor cycle,
            # 3 plant cycles need to have passed. So, using the plant cycle
            # count as reference, the sensor needs to sample at cycles:
            # [0, 3, 6, 8, 12, ..., 600]
            p_cycles_per_s_cycle = \
                self._plant_freq // sensor.sampling_frequency
            for trigger in range(0, self._plant_freq, p_cycles_per_s_cycle):
                if trigger not in self._cycle_triggers:
                    self._cycle_triggers[trigger] = []

                self._cycle_triggers[trigger].append(sensor)

            # set up underlying recorder
            record_fields = ['plant_seq']
            opt_record_fields = {}
            for prop in self._prop_sensors.keys():
                record_fields.append(f'{prop}_value')
                opt_record_fields[f'{prop}_sample'] = np.nan

            self._records = NamedRecordable(
                name=self.__class__.__name__,
                record_fields=record_fields,
                opt_record_fields=opt_record_fields
            )

    def get_sensor_rates(self) -> Mapping[str, int]:
        return {prop: sensor.sampling_frequency
                for prop, sensor in self._prop_sensors.items()}

    def process_plant_state(self,
                            plant_cycle: int,
                            prop_values: PhyPropMapping) \
            -> Dict[str, PhyPropType]:
        """
        Processes measured properties by passing them to the internal
        collection of sensors and returns the processed values.

        Parameters
        ----------
        plant_cycle
            The cycle number of the plant, used for determining which sensors
            should fire.
        prop_values
            Dictionary containing mappings from property names to measured
            values.

        Returns
        -------
        Dict
            A dictionary containing mappings from property names to processed
            sensor values.

        """
        cycle = plant_cycle % self._plant_freq
        sensor_samples = dict()
        try:
            # check which sensors need to be updated this cycle
            for sensor in self._cycle_triggers[cycle]:
                try:
                    prop_name = sensor.measured_property_name
                    value = prop_values[prop_name]
                    sensor_samples[prop_name] = sensor.process_sample(value)
                except KeyError:
                    raise MissingPropertyError(
                        'Missing expected update for property '
                        f'{sensor.measured_property_name}!')
            return sensor_samples
        except KeyError:
            # no sensors on this cycle
            raise NoSensorUpdate()
        finally:
            # record stuff
            record = {
                'plant_seq': plant_cycle,
            }

            for prop in self._prop_sensors.keys():
                record[f'{prop}_value'] = prop_values.get(prop, np.nan)
                record[f'{prop}_sample'] = sensor_samples.get(prop)

            self._records.push_record(**record)

    @property
    def recorders(self) -> Set[Recorder]:
        return self._records.recorders

    @property
    def record_fields(self) -> Sequence[str]:
        return self._records.record_fields
