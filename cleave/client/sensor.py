from abc import ABC, abstractmethod
from threading import RLock
from typing import Any


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
