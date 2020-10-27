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
from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Set

import numpy as np
from twisted.internet.protocol import Factory, Protocol, connectionDone

from ..logging import Logger
from ..util import PhyPropMapping


def _process_np_to_list(data: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: (v.tolist() if isinstance(v, np.ndarray) else v)
            for k, v in data.items()}


class Sink(Protocol):
    def __init__(self, parent_factory: _SinkFactory):
        self._fact = parent_factory

    def dataReceived(self, data: bytes):
        # do nothing on data received
        self._fact.log.warn(
            f'Received data on a outbound-only sink {self}!')
        return

    def write_data(self, data: str, end: str = os.linesep):
        self.transport.write(f'{data}{end}')

    def connectionMade(self):
        self._fact.log.info('New sink attached.')

    def connectionLost(self, reason=connectionDone):
        super(Sink, self).connectionLost(reason=reason)
        self._fact.remove_sink(self)


class _SinkFactory(Factory):
    def __init__(self):
        self._sinks: Set[Sink] = set()
        self._log = Logger()

    @property
    def log(self) -> Logger:
        return self._log

    def write_to_sinks(self, data: str, end: str = os.linesep):
        for s in self._sinks:
            s.write_data(data, end=end)

    def remove_sink(self, sink: Sink):
        self._sinks.remove(sink)
        self._log.info('Sink removed.')

    def buildProtocol(self, addr: Any) -> Sink:
        proto = Sink(self)
        self._sinks.add(proto)
        return proto


class PlantStateSinkFactory(_SinkFactory):
    def write_state(self,
                    timestamp: float,
                    raw_sensor_values: PhyPropMapping,
                    raw_actuator_values: PhyPropMapping,
                    proc_sensor_values: PhyPropMapping = {},
                    proc_actuator_values: PhyPropMapping = {}) -> None:
        state = {
            'timestamp': timestamp,
            'raw'      : {
                'sensors'  : _process_np_to_list(raw_sensor_values),
                'actuators': _process_np_to_list(raw_actuator_values),
            },
            'processed': {
                'sensors'  : _process_np_to_list(proc_sensor_values),
                'actuators': _process_np_to_list(proc_actuator_values)
            }
        }
