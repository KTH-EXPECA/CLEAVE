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
from threading import Condition
from typing import Any, Callable

from twisted.internet.posixbase import PosixReactorBase
from twisted.internet.threads import deferToThreadPool
from twisted.python.failure import Failure

from ..logging import Logger
from ..util import PhyPropMapping


class Controller(ABC):
    """
    Base class for controllers. This class defines a a simple interface that
    extending subclasses need to implement.
    """

    def __init__(self):
        super(Controller, self).__init__()

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


class BusyControllerException(Exception):
    pass


class ControllerWrapper:
    def __init__(self,
                 controller: Controller,
                 reactor: PosixReactorBase):
        super(ControllerWrapper, self).__init__()
        self._controller = controller
        self._reactor = reactor
        self._busy_cond = Condition()
        self._busy = False
        self._log = Logger()

    def process_sensor_samples(self,
                               samples: PhyPropMapping,
                               callback: Callable[[PhyPropMapping], Any]) \
            -> None:
        def process() -> PhyPropMapping:
            with self._busy_cond:
                if self._busy:
                    raise BusyControllerException()
                self._busy = True

            return self._controller.process(samples)

        def busy_errback(fail: Failure) -> None:
            fail.trap(BusyControllerException)
            self._log.warn('Controller is busy, discarding received samples.')

        def process_callback(actuation: PhyPropMapping) -> None:
            with self._busy_cond:
                self._busy = False
            callback(actuation)

        deferred = deferToThreadPool(self._reactor,
                                     self._reactor.getThreadPool(),
                                     process)
        deferred.addCallback(process_callback)
        deferred.addErrback(busy_errback)
