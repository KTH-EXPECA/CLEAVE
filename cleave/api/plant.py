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

#: This module contains the base API components for implementing and
#: extending arbitrary simulations of physical plants which are executed in
#: the context of the CLEAVE framework.

import json
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Optional

from .util import PhyPropMapping, PhyPropType
from ..core.client.statebase import BaseSemanticVariable, StateBase


class UnrecoverableState(Exception):
    def __init__(self, prop_values: PhyPropMapping):
        super(UnrecoverableState, self).__init__(
            json.dumps(prop_values, indent=4)
        )


class ControllerParameter(BaseSemanticVariable):
    """
    Note: Parameter from plant to controller is not yet implemented.

    A semantically significant variable corresponding to an initialization
    parameter for a controller interacting with this plant.

    Variables of this type will automatically be provided to the controller
    on initialization
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

            # if it has a sanity check, register it
            if value.sanity_check is not None:
                self._sanity_checks[key] = value.sanity_check

            # unpack value to discard wrapper object
            value = value.value
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


class Sensor(ABC):
    """
    This class defines an interface for sensors attached to a simulated plant.
    Implementations should override the process_sample() method with their
    logic.
    """

    # TODO: make Sensors and Actuators share a base class?

    def __init__(self, prop_name: str, sample_freq: int):
        """
        Parameters
        ----------
        prop_name
            Name of the property this sensor measures.
        sample_freq
            Sampling frequency of this sensor.
        """

        self._prop_name = prop_name
        self._sample_freq = sample_freq
        self._value = None

    @property
    def measured_property_name(self) -> str:
        """

        Returns
        -------
        str
            Name of the property monitored by this sensor.

        """
        return self._prop_name

    @property
    def sampling_frequency(self) -> int:
        """

        Returns
        -------
        int
            Sampling frequency of this sensor, expressed in Hertz.

        """
        return self._sample_freq

    @abstractmethod
    def process_sample(self, value: PhyPropType) -> PhyPropType:
        """
        Processes the measured value. This method should be implemented by
        subclasses to include sensor-specific behaviors.

        Parameters
        ----------
        value
            The latest measurement of the monitored property.

        Returns
        -------
        PhyPropType
            A possibly transformed value of the monitored property, according to
            the internal parameters of this sensor.

        """
        pass


class SimpleSensor(Sensor):
    """
    Simplest implementation of a sensor, which performs no processing on the
    read value and returns it as-is.
    """

    def process_sample(self, value: PhyPropType) -> PhyPropType:
        return value


class Actuator(ABC):
    """
    Abstract core class for actuators. Implementations should override the
    set_value() and get_actuation() methods with their logic.
    """

    def __init__(self, prop_name: str):
        """
        Parameters
        ----------
        prop_name
            Name of the property actuated upon by this actuator.
        """
        super(Actuator, self).__init__()
        self._prop_name = prop_name

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
    def set_value(self, desired_value: PhyPropType) -> None:
        """
        Called to set the target value for this actuator. This method should
        be implemented by extending classes.

        Parameters
        ----------
        desired_value
            Target value for this actuator.

        Returns
        -------

        """
        pass

    @abstractmethod
    def get_actuation(self) -> PhyPropType:
        """
        Returns the next value for the actuation processed governed by this
        actuator. This method should be implemented by extending classes.

        Returns
        -------
        PhyPropType
            A value for the actuated property.
        """
        pass


class SimpleConstantActuator(Actuator):
    """
    Implementation of a perfect actuator which keeps its value after being
    read (i.e. can be thought of as applying a constant force/actuation on
    the target variable).
    """

    def __init__(self, initial_value: PhyPropType, prop_name: str):
        super(SimpleConstantActuator, self).__init__(prop_name)
        self._value = initial_value

    def set_value(self, desired_value: PhyPropType) -> None:
        """
        Sets the value of the actuated property governed by this actuator.

        Parameters
        ----------
        desired_value
            The value of the actuated property.

        Returns
        -------

        """
        self._value = desired_value

    def get_actuation(self) -> PhyPropType:
        """
        Returns
        -------
        PhyPropType
            The current value of the actuated property.
        """
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
        super(SimpleImpulseActuator, self).__init__(prop_name=prop_name)
        self._default_value = default_value
        self._value = default_value

    def set_value(self, desired_value: PhyPropType) -> None:
        """
        Sets the next value returned by this actuator.

        Parameters
        ----------
        desired_value
            Value returned in the next call to get_actuation().
        Returns
        -------

        """
        self._value = desired_value

    def get_actuation(self) -> PhyPropType:
        """
        Returns the internally stored value, and then resets it to the
        default value.

        Returns
        -------
        PhyPropType
            The actuation value.
        """
        try:
            return self._value
        finally:
            self._value = self._default_value


class GaussianConstantActuator(SimpleConstantActuator):
    """
    Implementation of an actuator with Gaussian noise in its output.
    """

    def __init__(self,
                 prop_name: str,
                 g_mean: float,
                 g_std: float,
                 initial_value: Optional[PhyPropType] = None,
                 prealloc_size: int = int(1e6)):
        super(GaussianConstantActuator, self).__init__(
            prop_name=prop_name, initial_value=initial_value)
        import numpy
        self._random = numpy.random.default_rng()
        self._noise_mean = g_mean
        self._noise_std = g_std
        self._noise_prealloc = prealloc_size
        self._value = initial_value

        # preallocate values for efficiency
        self._noise = deque(self._random.normal(
            loc=self._noise_mean, scale=self._noise_std,
            size=self._noise_prealloc
        ))

    def set_value(self, desired_value: PhyPropType) -> None:
        try:
            noise = self._noise.pop()
        except IndexError:
            # empty stack, refill it
            self._noise = deque(self._random.normal(
                loc=self._noise_mean, scale=self._noise_std,
                size=self._noise_prealloc
            ))
            noise = self._noise.pop()

        super(GaussianConstantActuator, self).set_value(desired_value + noise)
