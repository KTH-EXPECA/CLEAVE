from typing import Dict

from .actuator import Actuator
from .sensor import Sensor
from ..network import ClientCommHandler
from ..util import PhyPropType


class Plant:
    def attach_sensor(self, sensor: Sensor):
        pass

    def attach_actuator(self, actuator: Actuator):
        pass

    def attach_commhandler(self, comm: ClientCommHandler):
        pass

    def advance_simulation(self,
                           dt_ns: int,
                           act_values: Dict[str, PhyPropType]):
        pass

    def execute(self):
        pass
