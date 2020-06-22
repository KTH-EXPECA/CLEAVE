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
from typing import Any, Callable, Dict, Optional

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
                logger.debug('Calling {function}', function=name, enqueue=True)
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
        """
        Parameters
        ----------
        dt
            Time interval in seconds between successive simulation steps.
        init_state
            Initial plant state.
        sensor
            BaseSensor instance associated with the plant.
        actuator
            BaseActuator instance associated with the plant.
        """
        super(Plant, self).__init__()
        logger.debug('Initializing plant.', enqueue=True)

        self._state = init_state
        self._state_lck = RLock()

        self._dt = dt
        self._step_cnt = 0

        self._sensor = sensor
        self._actuator = actuator

        self._shutdown_event = Event()
        self._shutdown_event.clear()

        # set up hooks
        self._start_of_step_hooks = HookCollection()
        self._end_of_step_hooks = HookCollection()
        self._pre_sim_hooks = HookCollection()

    def hook_start_of_step(self, fn: Callable[[], ...]):
        """
        Register a callable to be called at the beginning of each simulation
        step. This callable should take no arguments.

        The intended use pattern for this method is as a decorator.

        Parameters
        ----------
        fn
            Callable to be invoked at the start of each simulation step.
        """
        self._start_of_step_hooks.add(fn)

    def hook_end_of_step(self, fn: Callable[[], ...]):
        """
        Register a callable to be called at the end of each simulation
        step. This callable should take no arguments.

        The intended use pattern for this method is as a decorator.

        Parameters
        ----------
        fn
            Callable to be invoked at the end of each simulation step.
        """
        self._end_of_step_hooks.add(fn)

    def hook_pre_sim(self, fn: Callable[[Any], ...]):
        """
        Register a callable to be called immediately before advancing the
        state of the simulation, but after the initial procedures of each
        simulation step. This callable should take an optional `actuation`
        keyword argument through which it will receive the actuation command
        about to be applied to the state.

        The intended use pattern for this method is as a decorator.

        Parameters
        ----------
        fn
            Callable to be invoked right before advancing the simulation state.
        """

        self._pre_sim_hooks.add(fn)

    def shutdown(self):
        """
        Shuts down this plant.
        """

        # TODO: might need to do more stuff here at some point
        logger.warning('Shutting down plant.', enqueue=True)
        self._shutdown_event.set()

    def sample_state(self) -> BaseState:
        """
        Returns the current state of the plant. Thread- and process-safe.

        Returns
        -------
        BaseState
            Current state of the plant.
        """
        with self._state_lck:
            return self._state

    def _step(self):
        """
        Executes all the necessary procedures to advance the simulation a
        single discrete time step. This method calls the respective hooks,
        polls the actuator, advances the state and updates the actuator.
        """
        self._start_of_step_hooks.call()

        # pull next actuation command from actuator
        actuation = self._actuator.get_next_actuation()
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

            self._step_cnt += 1
            time.sleep(max(self._dt - time.time() + ti, 0))
