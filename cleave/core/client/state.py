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
import time
from abc import ABC, abstractmethod
from copy import copy
from typing import Set

from .semantics import BaseSemanticVariable
from ...api.plant import ActuatorVariable, ControllerParameter, SensorVariable

from ..logging import Logger
from ..util import PhyPropMapping


class StateError(Exception):
    pass


class StateWarning(Warning):
    pass


class State(ABC):
    """
    Abstract core class defining an interface for Plant state evolution over
    the course of a simulation. Implementing classes need to extend the
    advance() method to implement their logic, as this method will be called
    by the plant on each emulation time step.
    """

    # TODO: wrap this class in another class to avoid exposing internal use
    #  methods.

    def __new__(cls, *args, **kwargs):
        inst = ABC.__new__(cls)
        # call setattr on ABC since we are overriding it in this class and we
        # want to use the core implementation for these special variables
        ABC.__setattr__(inst, '_sensor_vars', set())
        ABC.__setattr__(inst, '_actuator_vars', set())
        ABC.__setattr__(inst, '_controller_params', set())
        ABC.__setattr__(inst, '_record_vars', set())
        return inst

    def __init__(self, update_freq_hz: int):
        super(State, self).__init__()
        self._freq = update_freq_hz
        self._ti = time.monotonic()
        self._log = Logger()

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

    @property
    def update_frequency(self) -> int:
        return self._freq

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

    def get_sensed_prop_names(self) -> Set[str]:
        """
        Returns
        -------
        Set
            Set containing the identifiers of the sensed variables.
        """
        return copy(self._sensor_vars)

    def get_actuated_prop_names(self) -> Set[str]:
        """
        Returns
        -------
        Set
            Set containing the identifiers of the actuated variables.
        """
        return copy(self._actuator_vars)

    def state_update(self,
                     control_cmds: PhyPropMapping,
                     delta_t: float) -> PhyPropMapping:
        """
        Performs a single step update using the give actuation values as
        inputs and returns the updated values for the sensed variables.

        Parameters
        ----------
        control_cmds
            Actuation inputs.
        delta_t
            Seconds since the previous call to this method.

        Returns
        -------
        PhyPropMapping
            Mapping from sensed property names to values.

        """
        for name, val in control_cmds.items():
            try:
                assert name in self._actuator_vars
                setattr(self, name, val)
            except AssertionError:
                self._log.warn('Received update for unregistered actuated '
                               f'property "{name}", skipping...')

        self.advance(delta_t)
        return {var: getattr(self, var) for var in self._sensor_vars}

    def get_variable_record(self) -> PhyPropMapping:
        """
        Returns
        -------
        PhyPropMapping
            A mapping containing the values of the recorded variables in
            this state.
        """
        return {var: getattr(self, var, None) for var in self._record_vars}

    def get_controller_parameters(self) -> PhyPropMapping:
        """
        Returns
        -------
        PhyPropMapping
            A mapping from strings to values containing the initialization
            parameters for the controller associated with this physical
            simulation.
        """

        return {var: getattr(self, var) for var in self._controller_params}
