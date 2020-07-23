from __future__ import annotations

import time
import warnings
from abc import ABC, abstractmethod
from threading import Event
from typing import Dict

from .actuator import Actuator, ActuatorArray
from .sensor import Sensor, SensorArray
from ..network.handler import ClientCommHandler
from ..util import PhyPropType

__all__ = ['Plant', 'State', 'PlantBuilder']


class PlantBuilderWarning(Warning):
    pass


class EmulationWarning(Warning):
    pass


class State(ABC):
    """
    Abstract base class defining an interface for Plant state evolution over
    the course of a simulation. Implementing classes need to extend the
    advance() method to implement their logic, as this method will be called
    by the plant on each emulation time step.
    """

    @abstractmethod
    def advance(self,
                dt_ns: int,
                act_values: Dict[str, PhyPropType]) -> Dict[str, PhyPropType]:
        """
        Called by the plant on every time step to advance the emulation,
        passing the number of nanoseconds since the last time this method
        returned and a mapping from property names to actuator values.
        Should return a dictionary containing mappings from property names to
        values, in order to update the sensors of the associated plant.

        Parameters
        ----------
        dt_ns
            Time passed since this method last RETURNED, in nanoseconds. Note
            when this method is invoked for the first time, this value will
            correspond to the time passed since the plant was instantiated.

        act_values
            Dictionary containing mappings from property names to values
            corresponding to the latest updated from actuators (if any).

        Returns
        -------
        Dict
            Implementations should return a dictionary of mappings from property
            names to values, corresponding to the updated values of the desired
            measured properties for this plant.

        """
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
                 comm: ClientCommHandler):
        self._freq = update_freq
        self._state = state
        self._sensors = sensor_array
        self._actuators = actuator_array
        self._comm = comm
        self._last_tf = time.monotonic_ns()
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
        sensor_samples = self._state.advance(
            dt_ns=time.monotonic_ns() - self._last_tf,
            act_values=proc_act)
        self._last_tf = time.monotonic_ns()
        proc_sens = self._sensors.process_plant_state(sensor_samples)
        self._comm.send_sensor_values(proc_sens)
        self._cycles += 1

    def execute(self):
        target_dt_ns = (1.0 // self._freq) * 10e9
        try:
            self._comm.connect()
            self._shutdown_flag.clear()
            while not self._shutdown_flag.is_set():
                try:
                    ti = time.monotonic_ns()
                    self.__emu_step()
                    time.sleep(target_dt_ns - (time.monotonic_ns() - ti))
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
        actuators, as well as detaching the plant state and comm handler.

        Returns
        -------

        """
        self._sensors = []
        self._actuators = []
        self._comm_handler = None
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

    def set_comm_handler(self, handler: ClientCommHandler) -> None:
        """
        Sets the communication handler for the plant under construction.

        Note that any previously assigned communication handler will be
        overwritten by this operation.

        Parameters
        ----------
        handler
            A ClientCommHandler instance to assign to the plant.

        Returns
        -------

        """
        if self._comm_handler is not None:
            warnings.warn(
                'Replacing already set ClientCommHandler for plant.',
                PlantBuilderWarning
            )

        self._comm_handler = handler

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

    def build(self, plant_upd_freq: int) -> Plant:
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
                update_freq=plant_upd_freq,
                state=self._plant_state,
                sensor_array=SensorArray(
                    plant_freq=plant_upd_freq,
                    sensors=self._sensors),
                actuator_array=ActuatorArray(actuators=self._actuators),
                comm=self._comm_handler
            )
        finally:
            self.reset()
