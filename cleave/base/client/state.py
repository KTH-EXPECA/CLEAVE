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
import warnings
from abc import ABC, abstractmethod
from copy import copy
from typing import Generic, Mapping, Type, TypeVar

from ..util import PhyPropMapping

T = TypeVar('T', int, float, bool, bytes)


class _PhysPropVar(Generic[T]):
    def __init__(self, value: T):
        # self._persistent = persistent
        # self._default = default
        self._value = value

    def get_value(self) -> T:
        # try:
        return self._value
        # finally:
        #     if not self._persistent:
        #         self._value = self._default

    def set_value(self, value: T):
        self._value = value

    def get_type(self) -> Type:
        return type(self._value)


class SensorVariable(_PhysPropVar):
    pass


class ActuatorVariable(_PhysPropVar):
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
        ABC.__setattr__(inst, '_sensor_vars', set())
        ABC.__setattr__(inst, '_actuator_vars', set())
        return inst

    def __init__(self, update_freq_hz: int):
        super(State, self).__init__()
        self._freq = update_freq_hz
        self._ti = time.monotonic()

    def get_delta_t(self):
        # TODO: change to work with simclock?
        try:
            return time.monotonic() - self._ti
        finally:
            self._ti = time.monotonic()

    def __setattr__(self, key, value):
        if isinstance(value, _PhysPropVar):
            # registering a new physical property
            if isinstance(value, SensorVariable):
                self._sensor_vars.add(key)
            elif isinstance(value, ActuatorVariable):
                self._actuator_vars.add(key)
            else:
                raise StateError('Physical properties need to be either '
                                 'Actuator or Sensor properties.')

            # unpack value to discard wrapper object
            value = value.get_value()
        super(State, self).__setattr__(key, value)

    def get_sensor_values(self) -> PhyPropMapping:
        return {name: getattr(self, name) for name in self._sensor_vars}

    def get_actuator_values(self) -> PhyPropMapping:
        return {name: getattr(self, name) for name in self._actuator_vars}

    def _actuate(self, act: PhyPropMapping) -> None:
        for name, val in act.items():
            try:
                assert name in self._actuator_vars
                setattr(self, name, val)
                # self._actuator_vars[name].set_value(val)
            except AssertionError:
                # TODO: use logger
                warnings.warn('Received update for unregistered actuated '
                              f'property "{name}!"',
                              StateWarning)

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

    def get_sensed_props(self) -> Mapping[str, Type]:
        """
        Returns
        -------
            Mapping containing the identifiers of the sensed variables.
        """
        return copy(self._sensor_vars)

    def get_actuated_props(self) -> Mapping[str, Type]:
        """
        Returns
        -------
            Mapping containing the identifiers of the actuated variables.
        """
        return copy(self._actuator_vars)

    def state_update(self, act_values: PhyPropMapping) -> PhyPropMapping:
        self._actuate(act_values)
        self.advance()
        return self.get_sensor_values()
