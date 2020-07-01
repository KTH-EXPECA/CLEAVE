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
from typing import Any, Callable

from loguru import logger

from . import Actuator, BaseState, Sensor, utils
from .mproc import RunnableLoopContext, TimedRunnableLoop


class Plant(TimedRunnableLoop):
    """
    Base class providing general functionality to represent closed-loop
    control plants.
    """

    def __init__(self,
                 dt_ns: int,
                 init_state: BaseState,
                 sensor: Sensor,
                 actuator: Actuator):
        """
        Parameters
        ----------
        dt_ns
            Time interval in seconds between successive simulation steps.
        init_state
            Initial plant state.
        sensor
            BaseSensor instance associated with the plant.
        actuator
            BaseActuator instance associated with the plant.
        """
        super(Plant, self).__init__(dt_ns=dt_ns)
        logger.debug('Initializing plant.', enqueue=True)

        self._state = init_state
        self._last_update = time.monotonic_ns()
        self._step_cnt = 0

        self._sensor = sensor
        self._actuator = actuator

        # set up hooks
        self._start_of_step_hooks = utils.HookCollection()
        self._end_of_step_hooks = utils.HookCollection()
        self._pre_sim_hooks = utils.HookCollection()

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

    def _loop(self) -> None:
        """
        Executes all the necessary procedures to advance the simulation a
        single discrete time step. This method calls the respective hooks,
        polls the actuator, advances the state and updates the sensor.
        """

        self._start_of_step_hooks.call()

        # pull next actuation command from actuator
        actuation = self._actuator.get_next_actuation()
        self._pre_sim_hooks.call(actuation=actuation)

        sample = self._state.advance(
            dt_ns=time.monotonic_ns() - self._last_update,
            actuation=actuation
        )
        self._last_update = time.monotonic_ns()

        self._sensor.sample = sample
        self._end_of_step_hooks.call()
        self._step_cnt += 1

    def run(self) -> None:
        with RunnableLoopContext([self._sensor, self._actuator]):
            super(Plant, self).run()
