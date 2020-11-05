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
from typing import Generic, Mapping, Type, TypeVar

from ..logging import Logger
from ..util import PhyPropMapping

T = TypeVar('T', int, float, bool, bytes)


class StateVariable(Generic[T]):
    def __init__(self, value: T, record: bool = True):
        self._value = value
        self._record = record

    def get_value(self) -> T:
        return self._value

    def set_value(self, value: T):
        self._value = value

    def get_type(self) -> Type:
        return type(self._value)

    @property
    def record(self) -> bool:
        return self._record


class ControllerParameter(StateVariable):
    def __init__(self, value: T, record: bool = False):
        # by default, controller parameters are not recorded
        super(ControllerParameter, self).__init__(value, record)


class SensorVariable(StateVariable):
    pass


class ActuatorVariable(StateVariable):
    pass


class StateError(Exception):
    pass


class StateWarning(Warning):
    pass


class State(ABC):
    """
    Abstract base class defining an interface for Plant state evolution over
    the course of a simulation. Implementing classes need to extend the
    advance() method to implement their logic, as this method will be called
    by the plant on each emulation time step.
    """

    def __new__(cls, *args, **kwargs):
        inst = ABC.__new__(cls)
        # call setattr on ABC since we are overriding it in this class and we
        # want to use the base implementation for these special variables
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

    def get_delta_t(self):
        # TODO: change to work with simclock?
        try:
            return time.monotonic() - self._ti
        finally:
            self._ti = time.monotonic()

    def __setattr__(self, key, value):
        if isinstance(value, StateVariable):
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
    def advance(self) -> None:
        """
        Called by the plant on every time step to advance the emulation.
        """
        pass

    def on_shutdown(self) -> None:
        """
        Callback for clean shutdown in case it's needed.
        """
        pass

    def get_sensed_prop_names(self) -> Mapping[str, Type]:
        """
        Returns
        -------
            Set containing the identifiers of the sensed variables.
        """
        return copy(self._sensor_vars)

    def get_actuated_prop_names(self) -> Mapping[str, Type]:
        """
        Returns
        -------
            Set containing the identifiers of the actuated variables.
        """
        return copy(self._actuator_vars)

    def state_update(self, control_cmds: PhyPropMapping) -> PhyPropMapping:
        for name, val in control_cmds.items():
            try:
                assert name in self._actuator_vars
                setattr(self, name, val)
            except AssertionError:
                self._log.warn('Received update for unregistered actuated '
                               f'property "{name}", skipping...')

        self.advance()
        return {var: getattr(self, var) for var in self._sensor_vars}

    def get_variable_record(self) -> PhyPropMapping:
        """
        Returns
        -------
            A mapping containing the values of the recorded variables in
            this state.
        """
        return {var: getattr(self, var, None) for var in self._record_vars}

    def get_controller_parameters(self) -> PhyPropMapping:
        """
        Returns
        -------
            A mapping from strings to values containing the initialization
            parameters for the controller associated with this physical
            simulation.
        """

        return {var: getattr(self, var) for var in self._controller_params}
