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
from typing import Generic, Mapping, Optional, TypeVar

from ..util import PhyPropType

T = TypeVar('T', int, float, bool, bytes)


class _PhysPropVar(Generic[T]):
    def __init__(self,
                 persistent: bool = True,
                 default: Optional[T] = None):
        self._persistent = persistent
        self._default = default
        self._value = default

    def get_value(self) -> T:
        try:
            return self._value
        finally:
            if not self._persistent:
                self._value = self._default

    def set_value(self, value: T):
        self._value = value


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
        ABC.__setattr__(inst, '_sensor_vars', {})
        ABC.__setattr__(inst, '_actuator_vars', {})
        return inst

    def __init__(self, update_freq_hz: int):
        super(State, self).__init__()
        # self.__sensor_vars: Dict[str, SensorVariable] = {}
        # self.__actuator_vars: Dict[str, ActuatorVariable] = {}

        self._freq = update_freq_hz
        self._ti = time.monotonic_ns()

    def get_delta_t_ns(self):
        try:
            return time.monotonic_ns() - self._ti
        finally:
            self._ti = time.monotonic_ns()

    def __setattr__(self, key, value):
        if isinstance(value, _PhysPropVar):
            # registering a new physical property
            if isinstance(value, SensorVariable):
                self._sensor_vars[key] = value
            elif isinstance(value, ActuatorVariable):
                self._actuator_vars[key] = value
            else:
                raise StateError('Physical properties need to be either '
                                 'Actuator or Sensor properties.')
        elif key in self._sensor_vars:
            # updating the value of a sensor variable
            self._sensor_vars[key].set_value(value)
        elif key in self._actuator_vars:
            self._actuator_vars[key].set_value(value)

        super(State, self).__setattr__(key, value)

    def __getattribute__(self, item):
        attr = super(State, self).__getattribute__(item)
        if isinstance(attr, _PhysPropVar):
            return attr.get_value()
        else:
            return attr

    def get_state(self) -> Mapping[str, PhyPropType]:
        return {name: p.get_value() for name, p in self._sensor_vars.items()}

    def actuate(self, act: Mapping[str, PhyPropType]) -> None:
        for name, val in act.items():
            try:
                self._actuator_vars[name].set_value(val)
            except KeyError:
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
