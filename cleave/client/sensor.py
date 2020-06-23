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

from __future__ import annotations

from abc import ABC, abstractmethod
from multiprocessing import Event, Process, RLock
from typing import Optional

from cleave.client import BaseState, utils


class BaseSensor(ABC, Process):
    def __init__(self, sample_freq: float):
        super(BaseSensor, self).__init__()
        self._state = None
        self._lock = RLock()
        self._freq = sample_freq
        self._ts = 1.0 / sample_freq
        self._shutdown_event = Event()
        self._shutdown_event.clear()

    def shutdown(self):
        self._shutdown_event.set()

    @property
    def sampling_freq(self) -> float:
        with self._lock:
            return self._freq

    @sampling_freq.setter
    def sampling_freq(self, value: float):
        with self._lock:
            self._freq = value
            self._ts = 1.0 / value

    @property
    def state(self) -> Optional[BaseState]:
        with self._lock:
            return self._state

    @state.setter
    def state(self, value: BaseState):
        with self._lock:
            self._state = value

    @abstractmethod
    def prepare_state(self, state: BaseState) -> bytes:
        pass

    @abstractmethod
    def send(self, payload: bytes):
        pass

    def _prepare_and_send_state(self):
        sample = self.prepare_state(self.state)
        self.send(sample)

    def run(self) -> None:
        utils.execute_periodically(
            fn=BaseSensor._prepare_and_send_state,
            period=self._ts,
            args=(self,),
            shutdown_flag=self._shutdown_event
        )
