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

from typing import Any, Dict, Mapping, NamedTuple, Sequence

import numpy as np
import pandas as pd
import scipy.stats


class MeanStdPair(NamedTuple):
    mean: float
    std: float


class RollingStatistics:
    def __init__(self,
                 columns: Sequence[str],
                 start_capacity: int = 1000,
                 missing_values: Any = np.nan):
        assert start_capacity > 0
        self._missing_value = missing_values
        self._columns = columns
        self._n_columns = len(columns)
        self._index = 0
        self._data = np.empty(shape=(start_capacity, self._n_columns),
                              dtype='float64')

    def to_pandas(self) -> pd.DataFrame:
        return pd.DataFrame(data=self._data[:self._index, :],
                            columns=self._columns)

    def rolling_window_stats(self, window_sz: int) -> Dict:
        window = self._data[
                 max(self._index - window_sz, 0):self._index, :]
        try:
            _, _, mean, var, *_ = scipy.stats.describe(window, axis=0)
            std = np.sqrt(var)

            return {
                c: MeanStdPair(m, s) for c, m, s in
                zip(self._columns, mean, std)
            }
        except ValueError:
            return {c: 0 for c in self._columns}

    def add_record(self, values: Mapping[str, Any]) -> None:
        self._data[self._index, :] = np.array(
            [values.get(col, self._missing_value) for col in self._columns]
        )
        self._index += 1

        if self._index >= self._data.shape[0]:
            self._data = np.vstack(self._data, np.empty(shape=self._data.shape))

# class ControllerStatCollector:
#     class Record(NamedTuple):
#         sensor_timestamp: float
#         sensor_rel_timestamp: int
#         sensor_payload: Mapping[str, PhyPropType]
#         process_dtime: float
#         act_timestamp: float
#         act_rel_timestamp: int
#         act_payload: Mapping[str, PhyPropType]
#
#     class PartialRecord:
#         def __init__(self,
#                      stat_collector: ControllerStatCollector,
#                      sensor_msg: ControlMessage):
#             self._sensor_timestamp = time.time()
#             self._sensor_rel_timestamp = stat_collector.get_reltime()
#             self._sensor_msg = sensor_msg
#             self._collector = stat_collector
#
#         def register_actuation(self, act_msg: ControlMessage):
#             assert act_msg.msg_type == ControlMsgType.ACTUATION_CMD
#             act_timestamp = time.time()
#             act_rel_timestamp = self._collector.get_reltime()
#             process_time = act_rel_timestamp - self._sensor_rel_timestamp /
#             10e9
#
#             # TODO register result with collector
#
#     def __init__(self):
#         self._exp_seq = 0
#         self._start_t_ns = time.monotonic_ns()
#         self._records
#
#     def get_reltime(self) -> int:
#         return time.monotonic_ns() - self._start_t_ns
#
#     def _reg_record(self):
#
#     def create_partial_record(self,
#                               sensor_msg: ControlMessage) -> PartialRecord:
#         # TODO: check sequence number!
#         assert sensor_msg.msg_type == ControlMsgType.SENSOR_SAMPLE
#         return self.PartialRecord(self, sensor_msg)
