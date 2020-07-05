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
from multiprocessing import RLock
from typing import Callable, Dict

from loguru import logger


# TODO: remove?
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
