from abc import ABC, abstractmethod
from typing import Any


class Actuator(ABC):
    def __init__(self, prop_name: str):
        super(Actuator, self).__init__()
        self._prop_name = prop_name
        self._value = None

    @property
    def actuated_property_name(self) -> str:
        return self._prop_name

    def apply_value(self, value: Any) -> None:
        self._value = value

    def get_actuator_value(self) -> Any:
        return self._process_actuation(self._value)

    @abstractmethod
    def _process_actuation(self, desired_value: Any) -> Any:
        pass


class SimpleActuator(Actuator):
    def _process_actuation(self, desired_value: Any) -> Any:
        return desired_value
