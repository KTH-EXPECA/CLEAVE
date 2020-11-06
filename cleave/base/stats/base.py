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
import abc
from collections import Collection, deque, namedtuple
from typing import Any, Mapping, Optional, Sequence


class IRecordBuffer(abc.ABC):
    @abc.abstractmethod
    def get_record_fields(self) -> Collection[str]:
        pass

    @abc.abstractmethod
    def pop_latest_records(self) -> Sequence[Mapping[str, Any]]:
        pass


class RecordBuffer(IRecordBuffer):
    def __init__(self,
                 record_fields: Collection[str],
                 max_records_in_memory: Optional[int] = None):
        self._record_cls = namedtuple('_Record', record_fields)
        self._record_fields = record_fields
        self._records = deque(maxlen=max_records_in_memory)

    def get_record_fields(self) -> Collection[str]:
        return self._record_fields

    def push_record(self, **kwargs) -> None:
        self._records.append(self._record_cls(**kwargs))

    def pop_latest_records(self) -> Sequence[Mapping[str, Any]]:
        try:
            return [r._asdict() for r in self._records]
        finally:
            self._records.clear()
