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
from pathlib import Path
from threading import RLock
from typing import Collection, Dict, Mapping

import pandas as pd
from twisted.logger import Logger

from cleave.base.sinks import Sink


class CSVStatCollector(Sink, abc.ABC):
    def __init__(self,
                 output_path: str,
                 chunksize: int = 1000):
        self._log = Logger()
        self._path = Path(output_path).resolve()
        if self._path.exists():
            if self._path.is_dir():
                raise FileExistsError(f'{self._path} exists and is a '
                                      f'directory!')
            self._log.warn(f'{self._path} will be overwritten with new data.')

        self._chunksize = chunksize
        self._chunk = [object()] * chunksize
        self._chunk_idx = 0
        self._chunk_count = 0

        # lock just in case, for the threaded IO operations
        self._lock = RLock()

    def on_start(self) -> None:
        self._log.info(f'Starting CSV writer on output path {self._path}')

    @abc.abstractmethod
    def _process_sunk_sample(self, values: Mapping) -> Dict:
        pass

    def flush_chunk_to_disk(self) -> threading.Thread:
        chunk = self._chunk[:self._chunk_idx].copy()
        chunk_count = self._chunk_count

        def _flush():
            with self._lock, self._path.open('a', newline='') as fp:
                df = pd.DataFrame(chunk)
                df.to_csv(fp, header=chunk_count == 0, index=False)

        # flush in separate thread to avoid locking up the GIL
        t = threading.Thread(target=_flush)
        t.start()

        self._chunk_idx = 0
        self._chunk_count += 1

        return t

    def sink(self, values: Mapping) -> None:
        self._chunk[self._chunk_idx] = self._process_sunk_sample(values)
        self._chunk_idx += 1

        if self._chunk_idx >= self._chunksize:
            # reached target chunksize, flush to disk on a separate thread
            self.flush_chunk_to_disk()

    def on_end(self) -> None:
        self._log.info(f'Flushing and closing CSV writer on path '
                       f'{self._path}...')
        self.flush_chunk_to_disk().join()  # wait for the final write


class PlantCSVStatCollector(CSVStatCollector):
    def __init__(self,
                 sensor_variables: Collection[str],
                 actuator_variables: Collection[str],
                 output_path: str,
                 chunksize: int = 1000):
        super(PlantCSVStatCollector, self).__init__(output_path=output_path,
                                                    chunksize=chunksize)
        # lists of sets to remove duplicates but get a consistent order
        self._sensor_vars = list(set(sensor_variables))
        self._actuator_vars = list(set(actuator_variables))

    def _process_sunk_sample(self, values: Mapping) -> Dict:
        # process the mapping provided to sink() into a flat dictionary
        # appropriate for a pandas dataframe
        time_dict = {
            'time_start': values['timestamps']['start'],
            'time_end'  : values['timestamps']['end'],
        }
        state_inputs = {f'state_input_{name}': v
                        for name, v in values['state']['inputs'].items()}
        state_outputs = {f'state_output_{name}': v
                         for name, v in values['state']['outputs'].items()}

        actuator_inputs = {f'act_input_{name}': v
                           for name, v in values['actuator_inputs'].items()}

        sensor_outputs = {f'sens_output_{name}': v
                          for name, v in values['sensor_outputs'].items()}

        return {**time_dict, **state_inputs, **state_outputs,
                **actuator_inputs, **sensor_outputs}
