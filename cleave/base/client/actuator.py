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

from abc import ABC, abstractmethod
from typing import Collection, Mapping, Optional

from ..logging import Logger
from ...base.util import PhyPropType


class RegisteredActuatorWarning(Warning):
    pass


class UnregisteredPropertyWarning(Warning):
    pass


class Actuator(ABC):
    """
    Abstract base class for actuators. Implementations should override the
    set_value() and get_actuation() methods with their logic.
    """

    def __init__(self,
                 prop_name: str,
                 start_value: Optional[PhyPropType] = None):
        super(Actuator, self).__init__()
        self._prop_name = prop_name
        self._value = start_value

    @property
    def actuated_property_name(self) -> str:
        """

        Returns
        -------
        str
            Name of the property actuated upon by this actuator.

        """
        return self._prop_name

    # TODO: Document this
    @abstractmethod
    def set_value(self, desired_value: PhyPropType) -> None:
        pass

    @abstractmethod
    def get_actuation(self) -> PhyPropType:
        pass


class SimpleConstantActuator(Actuator):
    """
    Implementation of a perfect actuator which keeps its value after being
    read (i.e. can be thought of as applying a constant force/actuation on
    the target variable).
    """

    def set_value(self, desired_value: PhyPropType) -> None:
        self._value = desired_value

    def get_actuation(self) -> PhyPropType:
        return self._value


class SimpleImpulseActuator(Actuator):
    """
    Implementation if a perfect actuator which resets its value after being
    read (i.e. can be thought as an actuator which applies impulses to the
    target variable).
    """

    def __init__(self,
                 prop_name: str,
                 default_value: PhyPropType):
        super(SimpleImpulseActuator, self).__init__(prop_name=prop_name,
                                                    start_value=default_value)
        self._default_value = default_value

    def set_value(self, desired_value: PhyPropType) -> None:
        self._value = desired_value

    def get_actuation(self) -> PhyPropType:
        try:
            return self._value
        finally:
            self._value = self._default_value


class ActuatorArray:
    """
    Internal utility class to manage a collection of Actuators attached to a
    Plant.
    """

    def __init__(self, actuators: Collection[Actuator]):
        super(ActuatorArray, self).__init__()
        self._log = Logger()
        self._actuators = dict()
        for actuator in actuators:
            if actuator.actuated_property_name in self._actuators:
                self._log.warn(
                    f'Replacing already registered sensor for property '
                    f'{actuator.actuated_property_name}'
                )

            self._actuators[actuator.actuated_property_name] = actuator

    def apply_actuation_inputs(self,
                               input_values: Mapping[str, PhyPropType]) \
            -> None:
        """
        Applies the desired actuation values to the internal actuators.

        Parameters
        ----------
        input_values
            Mapping from property names to desired actuation values.

        Returns
        -------

        """
        for prop, value in input_values.items():
            try:
                self._actuators[prop].set_value(value)
            except KeyError:
                self._log.warn(
                    f'Got actuation input for unregistered property {prop}!',
                    UnregisteredPropertyWarning
                )
                continue

    def get_actuation_values(self) -> Mapping[str, PhyPropType]:
        """
        Returns
        -------
            A mapping from actuated property names to output values from the
            corresponding actuators.
        """
        return {
            prop: act.get_actuation() for prop, act in self._actuators.items()
        }
