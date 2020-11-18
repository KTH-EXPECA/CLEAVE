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
from typing import Any

from cleave.core.client.statebase import BaseSemanticVariable, StateBase

__all__ = ['ControllerParameter', 'SensorVariable', 'ActuatorVariable', 'State']


class ControllerParameter(BaseSemanticVariable):
    """
    A semantically significant variable corresponding to an initialization
    parameter for a controller interacting with this plant.

    Variables of this type will automatically be provided to the controller
    on initialization (TODO: not implemented yet).
    """

    def __init__(self, value: Any, record: bool = False):
        # by default, controller parameters are not recorded
        super(ControllerParameter, self).__init__(value, record)


class SensorVariable(BaseSemanticVariable):
    """
    A semantically significant variable corresponding to a property measured
    by a sensor. Variables of this type will automatically be paired with the
    corresponding Sensor during emulation.
    """
    pass


class ActuatorVariable(BaseSemanticVariable):
    """
    A semantically significant variable corresponding to a property measured
    by an actuator. Variables of this type will automatically be paired with the
    corresponding Actuator during emulation.
    """
    pass


class State(StateBase, ABC):
    """
    Abstract core class defining an interface for Plant state evolution over
    the course of a simulation. Implementing classes need to extend the
    advance() method to implement their logic, as this method will be called
    by the plant on each emulation time step.
    """

    def __setattr__(self, key, value):
        if isinstance(value, BaseSemanticVariable):
            # registering a new physical property
            if isinstance(value, SensorVariable):
                self._sensor_vars.add(key)
            elif isinstance(value, ActuatorVariable):
                self._actuator_vars.add(key)
            elif isinstance(value, ControllerParameter):
                self._controller_params.add(key)

            # mark it as recordable or not
            if value.record:
                self._record_vars.add(key)

            # unpack value to discard wrapper object
            value = value.get_value()
        super(State, self).__setattr__(key, value)

    @abstractmethod
    def advance(self, delta_t: float) -> None:
        """
        Called by the plant on every time step to advance the emulation.
        Needs to be implemented by subclasses.

        Parameters
        ----------
        delta_t
            Time elapsed since the previous call to this method. This value
            will be 0 the first time this method is called.
        """
        pass

    def initialize(self) -> None:
        """
        Called by the plant at the beginning of the emulation.
        """
        pass

    def shutdown(self) -> None:
        """
        Called by the plant on shutdown.
        """
        pass
