from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import Any, Dict

from .actuator import Actuator, ActuatorArray
from .sensor import Sensor, SensorArray
from ..network.handler import ClientCommHandler
from ..util import PhyPropType


class PlantBuilderWarning(Warning):
    pass


class State(ABC):
    @abstractmethod
    def advance(self,
                dt_ns: int,
                act_values: Dict[str, PhyPropType]):
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
                 actuator_array: Any,
                 comm: ClientCommHandler):
        self._freq = update_freq
        self._state = state
        self._sensors = sensor_array
        self._actuators = actuator_array
        self._comm = comm

    def execute(self):
        # TODO
        pass

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
