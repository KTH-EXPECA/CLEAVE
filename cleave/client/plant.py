from __future__ import annotations

from abc import ABC

from .actuator import Actuator
from .sensor import Sensor
from .state import State
from ..network.handler import ClientCommHandler


class PlantBuilder:
    # noinspection PyAttributeOutsideInit
    def reset(self):
        self._sensors = []
        self._actuators = []
        self._comm_handler = None
        self._plant_freq = -1
        self._plant_state = None

    def __init__(self):
        self.reset()

    def attach_sensor(self, sensor: Sensor):
        pass

    def attach_actuator(self, actuator: Actuator):
        pass

    def attach_comm_handler(self, handler: ClientCommHandler):
        pass

    def set_update_rate(self, rate_hz: int):
        pass

    def set_plant_state(self, plant_state: State):
        pass

    def build(self) -> Plant:
        # TODO: build plant and reset
        self.reset()
        pass


class Plant(ABC):
    # interface for plant
    def execute(self):
        pass
