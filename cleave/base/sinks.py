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
import abc
from typing import Callable, Mapping

from cleave.base.util import PhyPropMapping, PhyPropType


class PlantSink(abc.ABC):
    @abc.abstractmethod
    def sink(self,
             timestamp: float,
             step_time: float,
             act_raw: PhyPropMapping,
             act_proc: PhyPropMapping,
             sens_raw: PhyPropMapping,
             sens_proc: PhyPropMapping):
        pass


class ControlSink(abc.ABC):
    @abc.abstractmethod
    def sink(self,
             sensor_data: PhyPropMapping,
             sensor_recv_time: float,
             actuator_data: PhyPropMapping,
             actuator_send_time: float):
        pass


def plant_sink(fn: Callable[[float,
                             float,
                             PhyPropMapping, PhyPropMapping,
                             PhyPropMapping, PhyPropMapping],
                            None]) -> PlantSink:
    class _PlantSinkWrapper(PlantSink):
        def sink(self,
                 timestamp: float,
                 step_time: float,
                 act_raw: PhyPropMapping,
                 act_proc: PhyPropMapping,
                 sens_raw: PhyPropMapping,
                 sens_proc: PhyPropMapping):
            fn(timestamp, step_time, act_raw, act_proc, sens_raw, sens_proc)

    return _PlantSinkWrapper()


def control_sink(fn: Callable[[PhyPropMapping, float,
                               PhyPropMapping, float], None]) -> ControlSink:
    class _ControlSinkWrapper(ControlSink):
        def sink(self,
                 sensor_data: PhyPropMapping,
                 sensor_recv_time: float,
                 actuator_data: PhyPropMapping,
                 actuator_send_time: float):
            fn(sensor_data, sensor_recv_time, actuator_data, actuator_send_time)

    return _ControlSinkWrapper()
