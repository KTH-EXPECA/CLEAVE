import warnings
from abc import ABC, abstractmethod
from typing import Collection, Dict

from ..util import PhyPropType


class RegisteredActuatorWarning(Warning):
    pass


class UnregisteredPropertyWarning(Warning):
    pass


class Actuator(ABC):
    def __init__(self, prop_name: str):
        super(Actuator, self).__init__()
        self._prop_name = prop_name
        self._value = None

    @property
    def actuated_property_name(self) -> str:
        return self._prop_name

    @abstractmethod
    def process_actuation(self, desired_value: PhyPropType) -> PhyPropType:
        pass


class SimpleActuator(Actuator):
    def process_actuation(self, desired_value: PhyPropType) -> PhyPropType:
        return desired_value


class ActuatorArray:
    def __init__(self, actuators: Collection[Actuator]):
        super(ActuatorArray, self).__init__()
        self._actuators = dict()
        for actuator in actuators:
            if actuator.actuated_property_name in self._actuators:
                warnings.warn(
                    f'Replacing already registered sensor for property '
                    f'{actuator.actuated_property_name}',
                    RegisteredActuatorWarning
                )

            self._actuators[actuator.actuated_property_name] = actuator

    def process_actuation_inputs(self, input_values: Dict[str, PhyPropType]) \
            -> Dict[str, PhyPropType]:
        processed_values = dict()
        for prop, value in input_values.items():
            try:
                processed_values[prop] = \
                    self._actuators[prop].process_actuation(value)
            except KeyError:
                warnings.warn(
                    f'Got actuation input for unregistered property {prop}!',
                    UnregisteredPropertyWarning
                )
                continue

        return processed_values
