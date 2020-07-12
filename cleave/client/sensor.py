import warnings
from abc import ABC, abstractmethod
from threading import RLock
from typing import Any, Dict


class RegisteredSensorWarning(Warning):
    pass


class UnregisteredPropertyWarning(Warning):
    pass


class IncompatibleFrequenciesError(Exception):
    pass


class MissingPropertyError(Exception):
    pass


class Sensor(ABC):
    def __init__(self, prop_name: str, fs: int):
        self._prop_name = prop_name
        self._sample_freq = fs
        self._lock = RLock()
        self._value = None

    @property
    def measured_property_name(self) -> str:
        return self._prop_name

    @property
    def sampling_frequency(self) -> Any:
        return self._sample_freq

    def write_value(self, value: Any) -> None:
        with self._lock:
            self._value = value

    def read_value(self) -> Any:
        with self._lock:
            return self.add_noise(self._value)

    @abstractmethod
    def add_noise(self, value: Any) -> Any:
        pass


class SimpleSensor(Sensor):
    def add_noise(self, value: Any) -> Any:
        return value


class SensorArray:
    def __init__(self, plant_freq: int):
        super(SensorArray, self).__init__()
        self._plant_freq = plant_freq
        self._prop_sensors = dict()
        self._cycle_triggers = dict()
        self._cycle_count = 0
        self._lock = RLock()

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

    def update_property_values(self, prop_values: Dict[str, Any]):
        with self._lock:
            try:
                # check which sensors need to be updated this cycle
                for sensor in self._cycle_triggers[self._cycle_count]:
                    try:
                        value = prop_values[sensor.measured_property_name]
                        sensor.write_value(value)
                    except KeyError:
                        raise MissingPropertyError(
                            'Missing expected update for property '
                            f'{sensor.measured_property_name}!')
            except KeyError:
                # no sensors on this cycle
                pass
            finally:
                self._cycle_count = (self._cycle_count + 1) % self._plant_freq
