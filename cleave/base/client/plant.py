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

from __future__ import annotations

import time
import warnings
from abc import ABC, abstractmethod
from threading import Event

from .actuator import Actuator, ActuatorArray
from .sensor import Sensor, SensorArray
from .state import State
from ...base.network import CommClient
from ...base.util import nanos2seconds, seconds2nanos

__all__ = ['Plant', 'PlantBuilder']


class PlantBuilderWarning(Warning):
    pass


class EmulationWarning(Warning):
    pass


class Plant(ABC):
    """
    Interface for all plants.
    """

    @abstractmethod
    def execute(self):
        """
        Executes this plant. Depending on implementation, this method may or
        may not be asynchronous.

        Returns
        -------

        """
        pass

    @property
    @abstractmethod
    def update_freq_hz(self) -> int:
        """
        The update frequency of this plant in Hz. Depending on
        implementation, accessing this property may or may not be thread-safe.

        Returns
        -------
        int
            The update frequency of the plant in Hertz.

        """
        pass

    @property
    @abstractmethod
    def plant_state(self) -> State:
        """
        The State object associated with this plant. Depending on
        implementation, accessing this property may or may not be thread-safe.

        Returns
        -------
        State
            The plant State.
        """
        pass


class _BasePlant(Plant):
    """
    Base, immutable implementation of a Plant.
    """

    def __init__(self,
                 update_freq: int,
                 state: State,
                 sensor_array: SensorArray,
                 actuator_array: ActuatorArray,
                 comm: CommClient):
        self._freq = update_freq
        self._state = state
        self._sensors = sensor_array
        self._actuators = actuator_array
        self._comm = comm
        self._cycles = 0

        self._shutdown_flag = Event()
        self._shutdown_flag.clear()

    def __emu_step(self):
        # 1. get raw actuation inputs
        # 2. process actuation inputs
        # 3. advance state
        # 4. process sensor outputs
        # 5. send sensor outputs

        act = self._comm.recv_actuator_values()
        proc_act = self._actuators.process_actuation_inputs(act)
        self._state.actuate(proc_act)
        self._state.advance()
        sensor_samples = self._state.get_state()
        proc_sens = self._sensors.process_plant_state(sensor_samples)
        self._comm.send_sensor_values(proc_sens)
        self._cycles += 1

    def execute(self):
        target_dt_ns = seconds2nanos(1.0 / self._freq)
        try:
            self._comm.connect()
            self._shutdown_flag.clear()
            while not self._shutdown_flag.is_set():
                try:
                    ti = time.monotonic_ns()
                    self.__emu_step()
                    time.sleep(nanos2seconds(
                        target_dt_ns - (time.monotonic_ns() - ti)))
                except ValueError:
                    warnings.warn(
                        'Emulation step took longer than allotted time slot!',
                        EmulationWarning
                    )
        except KeyboardInterrupt:
            self._shutdown_flag.set()
            warnings.warn(
                'Shutting down plant.',
                EmulationWarning
            )
        finally:
            self._comm.disconnect()

    @property
    def update_freq_hz(self) -> int:
        return self._freq

    @property
    def plant_state(self) -> State:
        return self._state

    @property
    def is_shutdown(self):
        return self._shutdown_flag.is_set()


# noinspection PyAttributeOutsideInit
class PlantBuilder:
    """
    Builder for plant objects.

    This class is not meant to be instantiated by users --- a library
    singleton is provided as cleave.client.builder.
    """

    def reset(self) -> None:
        """
        Resets this builder, removing all previously added sensors,
        actuators, as well as detaching the plant state and comm client.

        Returns
        -------

        """
        self._sensors = []
        self._actuators = []
        self._comm_client = None
        self._plant_state = None

    def __init__(self):
        self.reset()

    def attach_sensor(self, sensor: Sensor) -> None:
        """
        Attaches a sensor to the plant under construction.

        Parameters
        ----------
        sensor
            A Sensor instance to be attached to the target plant.


        Returns
        -------

        """
        self._sensors.append(sensor)

    def attach_actuator(self, actuator: Actuator) -> None:
        """
        Attaches an actuator to the plant under construction.

        Parameters
        ----------
        actuator
            An Actuator instance to be attached to the target plant.

        Returns
        -------

        """
        self._actuators.append(actuator)

    def set_comm_handler(self, client: CommClient) -> None:
        """
        Sets the communication client for the plant under construction.

        Note that any previously assigned communication handler will be
        overwritten by this operation.

        Parameters
        ----------
        client
            A ClientCommHandler instance to assign to the plant.

        Returns
        -------

        """
        if self._comm_client is not None:
            warnings.warn(
                'Replacing already set communication client for plant.',
                PlantBuilderWarning
            )

        self._comm_client = client

    def set_plant_state(self, plant_state: State) -> None:
        """
        Sets the State that will govern the evolution of the plant.

        Note that any previously assigned State will be overwritten by this
        operation.

        Parameters
        ----------
        plant_state
            A State instance to assign to the plant.

        Returns
        -------

        """
        if self._plant_state is not None:
            warnings.warn(
                'Replacing already set State for plant.',
                PlantBuilderWarning
            )

        self._plant_state = plant_state

    def build(self) -> Plant:
        """
        Builds a Plant instance and returns it. The actual subtype of this
        plant will depend on the previously provided parameters.

        Parameters
        ----------
        plant_upd_freq
            Update frequency of the built plant in Hz.

        Returns
        -------
        Plant
            A Plant instance.

        """

        # TODO: raise error if missing parameters OR instantiate different
        #  types of plants?
        try:
            return _BasePlant(
                update_freq=self._plant_state.update_frequency,
                state=self._plant_state,
                sensor_array=SensorArray(
                    plant_freq=self._plant_state.update_frequency,
                    sensors=self._sensors),
                actuator_array=ActuatorArray(actuators=self._actuators),
                comm=self._comm_client
            )
        finally:
            self.reset()
