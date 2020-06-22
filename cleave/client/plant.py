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
#   limitations under the License.
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from multiprocessing import Event, RLock
from typing import Callable, Dict, Optional

from loguru import logger

from .actuator import BaseActuationCommand, BaseActuator
from .sensor import BaseSensor


class BaseState(ABC):
    @abstractmethod
    def advance(self, actuation: Optional[BaseActuationCommand] = None) \
            -> BaseState:
        pass


class HookCollection:
    def __init__(self):
        self._lock = RLock()
        self._hooks: Dict[str, Callable] = {}

    def add(self, fn: Callable[[...], ...]):
        with self._lock:
            self._hooks[fn.__name__] = fn

    def remove(self, fn: Callable[[...], ...]):
        with self._lock:
            self._hooks.pop(fn.__name__, None)

    def call(self, *args, **kwargs):
        with self._lock:
            for name, hook in self._hooks.items():
                logger.debug('Calling {function}', function=name)
                hook(*args, **kwargs)


class Plant:
    """
    Base class providing general functionality to represent closed-loop
    control plants.
    """

    def __init__(self,
                 dt: float,
                 init_state: BaseState,
                 sensor: BaseSensor,
                 actuator: BaseActuator):
        super(Plant, self).__init__()
        logger.debug('Initializing plant.', enqueue=True)

        self._state = init_state
        self._state_lck = RLock()

        self.dt = dt
        self.step_cnt = 0

        self.sensor = sensor
        self.actuator = actuator

        self._shutdown_event = Event()
        self._shutdown_event.clear()

        # set up hooks
        self._start_of_step_hooks = HookCollection()
        self._end_of_step_hooks = HookCollection()
        self._pre_sim_hooks = HookCollection()

    def hook_start_of_step(self, fn: Callable[[...], ...]):
        self._start_of_step_hooks.add(fn)

    def hook_end_of_step(self, fn: Callable[[...], ...]):
        self._end_of_step_hooks.add(fn)

    def hook_pre_sim(self, fn: Callable[[...], ...]):
        self._pre_sim_hooks.add(fn)

    def shutdown(self):
        # TODO: might need to do more stuff here at some point
        logger.warning('Shutting down plant.', enqueue=True)
        self._shutdown_event.set()

    def _step(self):
        self._start_of_step_hooks.call()

        # pull next actuation command from actuator
        actuation = self.actuator.get_next_actuation()
        self._pre_sim_hooks.call(actuation=actuation)

        new_state = self._state.advance(actuation)
        with self._state_lck:
            self._state = new_state

        # TODO: sensor!

        self._end_of_step_hooks.call()

    def run(self):
        """
        Executes the simulation loop.
        """
        while not self._shutdown_event.is_set():
            ti = time.time()
            try:
                logger.debug('Executing simulation step.', enqueue=True)
                self._step()
                logger.debug('Finished simulation step', enqueue=True)
            except Exception as e:
                # TODO: descriptive exceptions
                logger.opt(exception=e).error('Caught exception!', enqueue=True)
                self.shutdown()
                return

            self.step_cnt += 1
            time.sleep(max(self.dt - time.time() + ti, 0))
