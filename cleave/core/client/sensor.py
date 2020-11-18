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

from typing import Collection, Dict, Mapping, Sequence, Set

import numpy as np

from ..logging import Logger
from ..recordable import NamedRecordable, Recordable, Recorder
from ...api.plant import Sensor
from ...api.util import PhyPropMapping

__all__ = ['SensorArray', 'NoSensorUpdate',
           'IncompatibleFrequenciesError', 'MissingPropertyError']


class IncompatibleFrequenciesError(Exception):
    pass


class MissingPropertyError(Exception):
    pass


class NoSensorUpdate(Exception):
    pass


class SensorArray(Recordable):
    """
    Internal utility class to manage a collection of Sensors attached to a
    Plant.
    """

    def __init__(self,
                 plant_tick_rate: int,
                 sensors: Collection[Sensor]):
        super(SensorArray, self).__init__()
        self._plant_tick_rate = plant_tick_rate
        self._prop_sensors = dict()
        self._cycle_triggers = dict()
        self._log = Logger()

        # TODO: add clock?

        # assign sensors to properties
        for sensor in sensors:
            if sensor.measured_property_name in self._prop_sensors:
                self._log.warn(f'Replacing already registered sensor for '
                               f'property {sensor.measured_property_name}')
            elif sensor.sampling_frequency > self._plant_tick_rate:
                raise IncompatibleFrequenciesError(
                    'Sensor sampling frequency cannot be higher than plant '
                    'update frequency!'
                )
            elif self._plant_tick_rate % sensor.sampling_frequency != 0:
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
                self._plant_tick_rate // sensor.sampling_frequency
            for trigger in range(0, self._plant_tick_rate,
                                 p_cycles_per_s_cycle):
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
                            prop_values: PhyPropMapping) -> PhyPropMapping:
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
        cycle = plant_cycle % self._plant_tick_rate
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
