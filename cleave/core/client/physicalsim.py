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
from typing import Sequence, Set

from .timing import SimTicker
from ..logging import Logger
from ..recordable import NamedRecordable, Recordable, Recorder
from ...api.plant import State, UnrecoverableState
from ...api.util import PhyPropMapping


class PhysicalSimulation(Recordable):
    def __init__(self, state: State, tick_rate: int):
        super(PhysicalSimulation, self).__init__()
        self._state = state

        self._tick_rate = tick_rate
        self._tick_dt = 1.0 / tick_rate

        self._log = Logger()
        self._ticker = SimTicker()

        self._act_vars = self._state.get_actuated_prop_names()
        self._sensor_vars = self._state.get_sensed_prop_names()

        tick_rec = ['tick', 'tick_dt']

        self._recordable = NamedRecordable(
            name=self.__class__.__name__,
            record_fields=tick_rec +
                          [f'input_{var}' for var in self._act_vars] +
                          [f'output_{var}' for var in self._sensor_vars]
        )

    @property
    def ticker(self) -> SimTicker:
        return self._ticker

    @property
    def recorders(self) -> Set[Recorder]:
        return self._recordable.recorders

    @property
    def record_fields(self) -> Sequence[str]:
        return self._recordable.record_fields

    @property
    def target_tick_rate(self) -> int:
        return self._tick_rate

    @property
    def target_tick_delta(self) -> float:
        return self._tick_dt

    @property
    def tick_count(self) -> int:
        return self._ticker.total_ticks

    def initialize(self) -> None:
        self._state.initialize()

    def shutdown(self) -> None:
        self._state.shutdown()

    def advance_state(self,
                      input_values: PhyPropMapping) -> PhyPropMapping:
        """
        Performs a single step update using the given actuation values as
        inputs and returns the updated values for the sensed variables.

        Parameters
        ----------
        input_values
            Actuation inputs.

        Returns
        -------
        PhyPropMapping
            Mapping from sensed property names to values.

        """
        record = {}

        for name, val in input_values.items():
            if name in self._act_vars:
                self._state.__setattr__(name, val)
                record[f'input_{name}'] = val
            else:
                self._log.warn('Received update for unregistered actuated '
                               f'property "{name}", skipping...')

        delta_t = self._ticker.tick()
        self._state.advance(delta_t)

        # sanity check!
        failed_sanity_check = self._state.check_semantic_sanity()
        if len(failed_sanity_check) > 0:
            # some variables failed their sanity check! (for instance,
            # maybe the plant is now unrecoverable since the inverted pendulum
            # exceeded some angle...)
            raise UnrecoverableState(failed_sanity_check)

        sensed_props = {}
        for name in self._sensor_vars:
            val = self._state.__getattribute__(name)
            sensed_props[name] = val
            record[f'output_{name}'] = val

        # record
        record['tick'] = self._ticker.total_ticks
        record['tick_dt'] = delta_t
        self._recordable.push_record(**record)

        return sensed_props
