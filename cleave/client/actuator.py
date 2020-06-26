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
from typing import Any, Optional

from .mproc import RunnableLoop


class BaseActuationCommand(ABC):
    @property
    @abstractmethod
    def payload(self) -> Any:
        pass


class BaseActuator(RunnableLoop, ABC):
    def __init__(self):
        super(BaseActuator, self).__init__()

    @abstractmethod
    def get_next_actuation(self) -> Optional[BaseActuationCommand]:
        pass

    @abstractmethod
    def listen(self) -> bytes:
        pass

    @abstractmethod
    def process_incoming(self, data: bytes):
        pass

    def _loop(self) -> None:
        self.process_incoming(self.listen())
