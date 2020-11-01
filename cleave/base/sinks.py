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
from typing import Callable, Collection, Mapping

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
