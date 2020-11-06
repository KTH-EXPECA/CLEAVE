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
from threading import RLock
from typing import Any, Mapping, Optional, Sequence


class IRecordBuffer(abc.ABC):
    @property
    @abc.abstractmethod
    def buffer_name(self) -> str:
        pass

    @abc.abstractmethod
    def get_record_fields(self) -> Collection[str]:
        pass

    @abc.abstractmethod
    def pop_latest_records(self) -> Sequence[Mapping[str, Any]]:
        pass


class RecordBuffer(IRecordBuffer):
    def __init__(self,
                 buffer_name: str,
                 record_fields: Collection[str],
                 opt_record_fields: Mapping[str, Any] = {},
                 max_records_in_memory: Optional[int] = None):
        self._name = buffer_name

        all_record_fields = list(record_fields) + list(opt_record_fields.keys())
        self._record_cls = namedtuple('_Record', all_record_fields,
                                      defaults=opt_record_fields.values())
        self._record_fields = record_fields
        self._records = deque(maxlen=max_records_in_memory)
        self._lock = RLock()

    @property
    def buffer_name(self) -> str:
        return self._name

    def get_record_fields(self) -> Collection[str]:
        return self._record_cls._fields

    def push_record(self, **kwargs) -> None:
        with self._lock:
            self._records.append(self._record_cls(**kwargs))

    def pop_latest_records(self) -> Sequence[Mapping[str, Any]]:
        with self._lock:
            try:
                return [r._asdict() for r in self._records]
            finally:
                self._records.clear()
