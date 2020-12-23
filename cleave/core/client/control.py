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
from abc import ABC, abstractmethod

from twisted.logger import Logger

from ...api.util import PhyPropMapping


class BaseControllerInterface(ABC):
    """
    Defines the core interface for interacting with controllers.
    """

    def __init__(self):
        self._log = Logger()

    @abstractmethod
    def put_sensor_values(self, prop_values: PhyPropMapping) -> None:
        """
        Send a sample of sensor values to the controller.

        Parameters
        ----------
        prop_values
            Mapping from property names to sensor values.
        """
        pass

    @abstractmethod
    def get_actuator_values(self) -> PhyPropMapping:
        """
        Waits for incoming data from the controller and returns a mapping
        from actuated property names to values.

        Returns
        -------
        Mapping
            Mapping from actuated property names to values.
        """
        pass


class DummyControllerInterface(BaseControllerInterface):
    def put_sensor_values(self, prop_values: PhyPropMapping) -> None:
        pass

    def get_actuator_values(self) -> PhyPropMapping:
        return {}
