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

from ..logging import Logger
from ...api.util import PhyPropMapping
from ...api.plant import State


class PhysicalSimulation:
    def __init__(self, state: State, tick_rate: int):
        super(PhysicalSimulation, self).__init__()
        self._state = state

        self._tick_rate = tick_rate
        self._tick_dt = 1.0 / tick_rate

        self._log = Logger()

        self._act_vars = self._state.get_actuated_prop_names()
        self._sensor_vars = self._state.get_sensed_prop_names()

    @property
    def tick_rate(self) -> int:
        return self._tick_rate

    @property
    def tick_delta(self) -> float:
        return self._tick_dt

    def initialize(self) -> None:
        self._state.initialize()

    def shutdown(self) -> None:
        self._state.shutdown()

    def advance_state(self,
                      control_cmds: PhyPropMapping,
                      delta_t: float) -> PhyPropMapping:
        """
        Performs a single step update using the given actuation values as
        inputs and returns the updated values for the sensed variables.

        Parameters
        ----------
        control_cmds
            Actuation inputs.
        delta_t
            Seconds since the previous call to this method.

        Returns
        -------
        PhyPropMapping
            Mapping from sensed property names to values.

        """
        # TODO: record!

        for name, val in control_cmds.items():
            try:
                assert name in self._act_vars
                self._state.__setattr__(name, val)
            except AssertionError:
                self._log.warn('Received update for unregistered actuated '
                               f'property "{name}", skipping...')

        self._state.advance(delta_t)
        return {var: self._state.__getattribute__(var)
                for var in self._sensor_vars}
