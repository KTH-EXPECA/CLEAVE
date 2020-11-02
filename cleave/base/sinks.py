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
import copy
import threading
from pathlib import Path
from threading import RLock
from typing import Callable, Collection, Dict, Mapping

import pandas as pd

from .logging import Logger


class Sink(abc.ABC):
    def on_start(self) -> None:
        pass

    def on_end(self) -> None:
        pass

    @abc.abstractmethod
    def sink(self, values: Mapping) -> None:
        pass


def make_sink(fn: Callable[[Mapping], None]) -> Sink:
    class _SinkWrapper(Sink):
        def sink(self, values: Mapping) -> None:
            return fn(values)

    return _SinkWrapper()


class SinkGroup(Sink):
    def __init__(self,
                 name: str,
                 sinks: Collection[Sink] = ()):
        self._log = Logger()
        self._name = name
        self._sinks = set(sinks)

    def on_start(self) -> None:
        self._log.info(f'Setting up sinks for group {self._name}...')
        for sink in self._sinks:
            sink.on_start()

    def on_end(self) -> None:
        self._log.info(f'Shutting down sinks for group {self._name}...')
        for sink in self._sinks:
            sink.on_end()

    def sink(self, values: Mapping) -> None:
        for sink in self._sinks:
            sink.sink(copy.deepcopy(values))

    def add_sink(self, sink: Sink):
        self._sinks.add(sink)

    def remove_sink(self, sink: Sink):
        self._sinks.remove(sink)


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
        t = threading.Thread(target=_flush).start()

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

        flat_dict = {
            'time_start': values['timestamps']['start'],
            'time_end'  : values['timestamps']['end'],
        }

        raw_sens = values['sensor_values']['raw']
        proc_sens = values['sensor_values']['processed']

        raw_act = values['actuator_values']['raw']
        proc_act = values['actuator_values']['processed']

        for v in self._sensor_vars:
            flat_dict[f'sensor_{v}_raw'] = raw_sens[v]
            flat_dict[f'sensor_{v}_proc'] = proc_sens.get(v, None)

        for v in self._actuator_vars:
            flat_dict[f'actuator_{v}_raw'] = raw_act[v]
            flat_dict[f'actuator_{v}_proc'] = proc_act.get(v, None)

        return flat_dict
