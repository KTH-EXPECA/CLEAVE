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


class PlantBuilderWarning(Warning):
    pass


class EmulationWarning(Warning):
    pass


class State(ABC):
    @abstractmethod
    def advance(self,
                dt_ns: int,
                act_values: Dict[str, PhyPropType]) -> Dict[str, PhyPropType]:
        pass


class Plant(ABC):
    # interface for plant
    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    @property
    def update_freq_hz(self) -> int:
        pass

    @abstractmethod
    @property
    def plant_state(self) -> State:
        pass


class BasePlant(Plant):
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
        # run the emulation loop
        target_dt_ns = (1.0 // self._freq) * 10e9
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

    @property
    def update_freq_hz(self) -> int:
        return self._freq

    @property
    def plant_state(self) -> State:
        return self._state


# noinspection PyAttributeOutsideInit
class PlantBuilder:
    def reset(self):
        self._sensors = []
        self._actuators = []
        self._comm_handler = None
        self._plant_state = None

    def __init__(self):
        self.reset()

    def attach_sensor(self, sensor: Sensor):
        self._sensors.append(sensor)

    def attach_actuator(self, actuator: Actuator):
        self._actuators.append(actuator)

    def set_comm_handler(self, handler: ClientCommHandler):
        if self._comm_handler is not None:
            warnings.warn(
                'Replacing already set ClientCommHandler for plant.',
                PlantBuilderWarning
            )

        self._comm_handler = handler

    def set_plant_state(self, plant_state: State):
        if self._plant_state is not None:
            warnings.warn(
                'Replacing already set State for plant.',
                PlantBuilderWarning
            )

        self._plant_state = plant_state

    def build(self, plant_upd_freq: int) -> Plant:
        try:
            return BasePlant(
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
