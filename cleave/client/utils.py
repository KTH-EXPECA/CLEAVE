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
from multiprocessing import Event, RLock
from typing import Callable, Dict, Optional, Tuple

from loguru import logger


def execute_periodically(fn: Callable[[...], None],
                         period_ns: int,
                         args: Optional[Tuple] = None,
                         kwargs: Optional[Dict] = None,
                         shutdown_flag: Event = Event()):
    shutdown_flag.clear()
    while not shutdown_flag.is_set():
        ti = time.monotonic_ns()
        fn(*args, **kwargs)
        dt = time.monotonic_ns() - ti
        try:
            time.sleep((dt - period_ns) / 1e9)
        except ValueError:
            logger.warning('Function {} execution took longer than given '
                           'period! dt = {} ns, period = {} ns',
                           fn.__name__, dt, period_ns, enqueue=True)


class HookCollection:
    def __init__(self):
        self._lock = RLock()
        self._hooks: Dict[str, Callable] = {}

    def add(self, fn: Callable[[...], ...]):
        with self._lock:
            self._hooks[fn.__name__] = fn

    def remove(self, fn: Callable[[...], ...]):
        with self._lock:
            self._hooks.pop(fn.__name__, None)

    def call(self, *args, **kwargs):
        with self._lock:
            for name, hook in self._hooks.items():
                logger.debug('Calling {function}', function=name, enqueue=True)
                hook(*args, **kwargs)
