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
import threading
from collections import Collection
from pathlib import Path
from threading import RLock
from typing import Any, Dict

import numpy as np
import pandas as pd

from ..logging import Logger


class TableLogger(abc.ABC):
    def __init__(self,
                 columns: Collection[str]):
        self._columns = sorted(set(columns))  # for consistent ordering

    def on_start(self):
        pass

    def on_end(self):
        pass

    @abc.abstractmethod
    def append_row(self, row: Dict[str, Any]):
        pass


class CSVTableLogger(TableLogger):
    def __init__(self,
                 output_path: str,
                 columns: Collection[str],
                 chunk_size: int = 1000):
        super(CSVTableLogger, self).__init__(columns)
        self._log = Logger()
        self._path = Path(output_path).resolve()
        if self._path.exists():
            if self._path.is_dir():
                raise FileExistsError(f'{self._path} exists and is a '
                                      f'directory!')
            self._log.warn(f'{self._path} will be overwritten with new data.')

        dummy_data = np.empty((chunk_size, len(self._columns)))
        self._table_chunk = pd.DataFrame(data=dummy_data, columns=self._columns)
        self._chunk_count = 0
        self._chunk_row_idx = 0

        self._lock = RLock()

    def on_start(self):
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

        self._chunk_idx = 0
        self._chunk_count += 1

        return t

    def append_row(self, row: Dict[str, Any]):
        self._table_chunk.iloc[self._chunk_row_idx] = pd.Series(row)
        self._chunk_row_idx += 1

        if self._chunk_row_idx == 0:
            # flush to disk
            self._flush_chunk_to_disk()

    def on_end(self) -> None:
        self._log.info(f'Flushing and closing CSV table writer on path '
                       f'{self._path}...')
        self._flush_chunk_to_disk().join()  # wait for the final write
