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
from abc import ABC, abstractmethod
from threading import RLock
from typing import Mapping

import msgpack

from ..util import PhyPropType


class Controller(ABC):
    class NoSamples(Exception):
        pass

    class InvalidInput(Exception):
        pass

    def __init__(self):
        super(Controller, self).__init__()
        self._lock = RLock()
        self._unpacker = msgpack.Unpacker()

    @abstractmethod
    def process(self, sensor_values: Mapping[str, PhyPropType]) \
            -> Mapping[str, PhyPropType]:
        pass

    def process_bytes(self, inputs: bytes) -> bytes:
        with self._lock:  # make sure processing is thread safe
            try:
                # unpack and parse the data
                self._unpacker.feed(inputs)
                sensor_samples = next(self._unpacker)
                if not isinstance(sensor_samples, dict):
                    raise Controller.InvalidInput(
                        f'Invalid input to controller: {sensor_samples}')
            except StopIteration:
                raise Controller.NoSamples()

            proc_result = self.process(sensor_samples)

        # pack results
        return msgpack.packb(proc_result, use_bin_type=True)
