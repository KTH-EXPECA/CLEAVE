from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import Collection, Dict

from ..util import PhyPropType

__all__ = ['Sensor', 'SimpleSensor', 'SensorArray']


class RegisteredSensorWarning(Warning):
    pass


class IncompatibleFrequenciesError(Exception):
    pass


class MissingPropertyError(Exception):
    pass


class Sensor(ABC):
    """
    Abstract base class for sensors. Implementations should override the
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


class SensorArray:
    """
    Internal utility class to manage a collection of Sensors attached to a
    Plant.
    """

    def __init__(self, plant_freq: int,
                 sensors: Collection[Sensor]):
        super(SensorArray, self).__init__()
        self._plant_freq = plant_freq
        self._prop_sensors = dict()
        self._cycle_triggers = dict()
        self._cycle_count = 0

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
            pcycles_per_scycle = \
                self._plant_freq // sensor.sampling_frequency
            for trigger in range(0, self._plant_freq, pcycles_per_scycle):
                if trigger not in self._cycle_triggers:
                    self._cycle_triggers[trigger] = []

                self._cycle_triggers[trigger].append(sensor)

    def process_plant_state(self,
                            prop_values: Dict[str, PhyPropType]) \
            -> Dict[str, PhyPropType]:
        """
        Processes measured properties by passing them to the internal
        collection of sensors and returns the processed values.

        Parameters
        ----------
        prop_values
            Dictionary containing mappings from property names to measured
            values.

        Returns
        -------
        Dict
            A dictionary containing mappings from property names to processed
            sensor values.

        """
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

            return processed_values
        except KeyError:
            # no sensors on this cycle
            pass
        finally:
            # always increase the cycle counter
            self._cycle_count = (self._cycle_count + 1) % self._plant_freq
