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

from abc import ABC, abstractmethod
from multiprocessing import Event, Process, RLock
from typing import Any, Optional


class BaseActuationCommand(ABC):
    @property
    @abstractmethod
    def payload(self) -> Any:
        pass


class BaseActuator(ABC, Process):
    def __init__(self):
        super(BaseActuator, self).__init__()
        self._lck = RLock()
        self._shutdown_flag = Event()
        self._shutdown_flag.set()

    def shutdown(self):
        self._shutdown_flag.set()

    @abstractmethod
    def get_next_actuation(self) -> Optional[BaseActuationCommand]:
        pass

    @abstractmethod
    def listen(self) -> bytes:
        pass

    @abstractmethod
    def process_incoming(self, data: bytes):
        pass

    def start(self) -> None:
        if self._shutdown_flag.is_set():
            super(BaseActuator, self).start()

    def run(self) -> None:
        self._shutdown_flag.clear()
        while not self._shutdown_flag.is_set():
            try:
                self.process_incoming(self.listen())
            except TimeoutError:
                pass
