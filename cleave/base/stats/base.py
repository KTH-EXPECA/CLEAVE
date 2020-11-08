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

import abc
import threading
from collections import Collection, deque, namedtuple
from pathlib import Path
from threading import RLock
from typing import Any, Mapping, NamedTuple, Optional, Sequence, Set

import numpy as np
import pandas as pd

from ..logging import Logger


class Recorder(abc.ABC):
    def record(self, recordable: Recordable):
        recordable.recorders.add(self)

    @abc.abstractmethod
    def notify(self, latest_record: NamedTuple):
        pass


class Recordable(abc.ABC):
    @property
    @abc.abstractmethod
    def recorders(self) -> Set[Recorder]:
        pass


class BaseRecordable(Recordable):
    def __init__(self,
                 name: str,
                 record_fields: Collection[str],
                 opt_record_fields: Mapping[str, Any] = {}):
        self._name = name
        self._recorders: Set[Recorder] = set()
        all_record_fields = list(record_fields) + list(opt_record_fields.keys())
        self._record_cls = namedtuple('_Record', all_record_fields,
                                      defaults=opt_record_fields.values())
        self._record_fields = record_fields

    def push_record(self, **kwargs) -> None:
        record = self._record_cls(**kwargs)
        for recorder in self._recorders:
            recorder.notify(record)

    @property
    def recorders(self) -> Set[Recorder]:
        return self._recorders


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


class RecordOutputStream(abc.ABC):
    def initialize(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    @abc.abstractmethod
    def push_record(self, record: Mapping[str, Any]) -> None:
        pass

    @abc.abstractmethod
    def push_records(self, records: Sequence[Mapping[str, Any]]) -> None:
        pass

    def flush(self) -> None:
        pass


class CSVRecordOutputStream(RecordOutputStream):
    def __init__(self,
                 output_path: str,
                 record_fields: Sequence[str],
                 chunk_size: int = 1000):
        self._log = Logger()
        self._path = Path(output_path).resolve()
        if self._path.exists():
            if self._path.is_dir():
                raise FileExistsError(f'{self._path} exists and is a '
                                      f'directory!')
            self._log.warn(f'{self._path} will be overwritten with new data.')

        dummy_data = np.empty((chunk_size, len(record_fields)))
        self._table_chunk = pd.DataFrame(data=dummy_data, columns=record_fields)
        self._chunk_count = 0
        self._chunk_row_idx = 0

        self._lock = RLock()

    def initialize(self) -> None:
        # "touch" the file to clear it and prepare for actual writing
        with self._path.open('wb') as fp:
            fp.write(bytes(0x00))

    def _flush_chunk_to_disk(self) -> threading.Thread:
        chunk = self._table_chunk.iloc[:self._chunk_row_idx].copy()
        count = self._chunk_count

        def _flush():
            with self._lock, self._path.open('a', newline='') as fp:
                chunk.to_csv(fp, header=(count == 0), index=False)

        # flush in separate thread to avoid locking up the GIL
        t = threading.Thread(target=_flush)
        t.start()

        self._chunk_row_idx = 0
        self._chunk_count += 1

        return t

    def flush(self) -> None:
        self._flush_chunk_to_disk()

    def push_record(self, record: Mapping[str, Any]) -> None:
        self._table_chunk.iloc[self._chunk_row_idx] = pd.Series(record)
        self._chunk_row_idx += 1

        if self._chunk_row_idx == self._table_chunk.shape[0]:
            # flush to disk
            self._flush_chunk_to_disk()

    def push_records(self, records: Sequence[Mapping[str, Any]]) -> None:
        # TODO: optimize, maybe?
        for record in records:
            self.push_record(record)

    def shutdown(self) -> None:
        self._log.info(f'Flushing and closing CSV table writer on path '
                       f'{self._path}...')
        self._flush_chunk_to_disk().join()  # wait for the final write
