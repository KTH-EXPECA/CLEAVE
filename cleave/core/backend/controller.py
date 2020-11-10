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
from queue import Empty
from typing import Callable

from ..util import PhyPropMapping, SingleElementQ


# TODO: refactor out all "internal use" methods from this class into a
#  wrapper class.

class Controller(ABC):
    """
    Base class for controllers. This class defines a a simple interface that
    extending subclasses need to implement.
    """

    def __init__(self):
        super(Controller, self).__init__()
        self._input_q = SingleElementQ()

    def submit_request(self,
                       control_input: PhyPropMapping,
                       callback: Callable[[PhyPropMapping], None], ) -> None:
        """
        (Internal use)

        Submits a actuation input to be processed in an asynchronous fashion.

        Parameters
        ----------
        control_input
            Mapping from property names to values corresponding to the
            desired values for the actuated properties of this plant.
        callback
            A callback function to be executed after advancing the
            simulation, for instance to send samples to the controller. A
            single parameter will be passed to this function, corresponding
            to the mapping from property names to values returned by the
            process() method of this class.

        Returns
        -------

        """
        self._input_q.put({'input': control_input, 'callback': callback})

    def process_loop(self):
        """
        (Internal use)

        Function intended to be used within the event loop of the controller
        for periodic processing of input samples.
        """

        try:
            control_req = self._input_q.pop_nowait()
        except Empty:
            return

        control_output = self.process(control_req['input'])
        control_req['callback'](control_output)

    @abstractmethod
    def process(self, sensor_values: PhyPropMapping) -> PhyPropMapping:
        """
        Processes samples and produces a control command.

        Samples arrive in the form of a dictionary of mappings from sensor
        property name to measured value. Actuator commands should be returned
        in the same fashion, in a dictionary of mappings from actuated
        property name to actuated value.

        This method needs to be implemented by extending subclasses with
        their respective logic.

        Parameters
        ----------
        sensor_values
            A mapping of sensor property names to measured values.

        Returns
        -------
        PhyPropMapping
            A mapping of actuated property names to desired values.

        """
        pass
