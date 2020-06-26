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
#   limitations under the License.
import time
from abc import ABC, abstractmethod
# noinspection PyProtectedMember
from typing import Collection

from loguru import logger
from multiprocess.context import _default_context
from multiprocess.pool import Pool
from multiprocess.synchronize import Event


class Runnable(ABC):
    @abstractmethod
    def run(self) -> None:
        pass


class RunnableLoop(Runnable, ABC):
    def __init__(self):
        super(RunnableLoop, self).__init__()
        self._shutdown_flag = Event(ctx=_default_context)
        self._shutdown_flag.set()

    @abstractmethod
    def _loop(self) -> None:
        pass

    def run(self) -> None:
        self._shutdown_flag.clear()
        while not self._shutdown_flag.is_set():
            self._loop()

    def shutdown(self) -> None:
        self._shutdown_flag.set()

    def is_shutdown(self) -> bool:
        return self._shutdown_flag.is_set()


class TimedRunnableLoop(RunnableLoop, ABC):
    def __init__(self, dt_ns: int):
        super(TimedRunnableLoop, self).__init__()
        self._dt_ns = dt_ns

    def run(self) -> None:
        self._shutdown_flag.clear()
        while not self._shutdown_flag.is_set():
            ti = time.monotonic_ns()
            self._loop()
            dt = time.monotonic_ns() - ti
            try:
                time.sleep((self._dt_ns - dt) / 1e9)
            except ValueError:
                logger.warning('self._loop execution took longer than given '
                               'period! dt = {} ns, period = {} ns',
                               dt, self._dt_ns, enqueue=True)


class RunnableLoopContext:
    def __init__(self, loops: Collection[RunnableLoop]):
        self._pool = Pool()
        self._loops = loops

    def __enter__(self):
        self._pool.__enter__()
        for loop in self._loops:
            self._pool.apply_async(loop.run)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for loop in self._loops:
            loop.shutdown()
        self._pool.__exit__(exc_type, exc_val, exc_tb)
