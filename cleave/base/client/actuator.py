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

import warnings
from abc import ABC, abstractmethod
from typing import Collection, Dict

from ...base.util import PhyPropType


class RegisteredActuatorWarning(Warning):
    pass


class UnregisteredPropertyWarning(Warning):
    pass


class Actuator(ABC):
    """
    Abstract base class for actuators. Implementations should override the
    process_actuation() method with their logic.
    """

    def __init__(self, prop_name: str):
        super(Actuator, self).__init__()
        self._prop_name = prop_name
        self._value = None

    @property
    def actuated_property_name(self) -> str:
        """

        Returns
        -------
        str
            Name of the property actuated upon by this actuator.

        """
        return self._prop_name

    @abstractmethod
    def process_actuation(self, desired_value: PhyPropType) -> PhyPropType:
        """
        Processes the raw actuation value obtained from the controller.
        Implementing subclasses should put their logic here, for instance to
        add noise to an actuation command.

        Parameters
        ----------
        desired_value
            Actuation value obtained from controller.

        Returns
        -------
        PhyPropType
            A possibly altered value of the actuated property, according to
            the internal parameters of this actuator.

        """
        pass


class SimpleActuator(Actuator):
    """
    Simplest implementation of an actuator, which performs no processing on the
    value obtained from the controller and returns it as-is.
    """

    def process_actuation(self, desired_value: PhyPropType) -> PhyPropType:
        return desired_value


class ActuatorArray:
    """
    Internal utility class to manage a collection of Actuators attached to a
    Plant.
    """

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
        """
        Processes the actuation inputs obtained from the controller by
        passing them to the internal collection of actuators and returning
        the processed values.

        Parameters
        ----------
        input_values
            A dictionary containing mappings from actuated property names to
            input values.

        Returns
        -------
        Dict
            A dictionary containing mappings from actuated property names to
            processed values.

        """
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
