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
from typing import Optional
from unittest import TestCase

from cleave.client import ActuationCommand, Actuator


class DummyActuator(Actuator):

    def get_next_actuation(self) -> Optional[ActuationCommand]:
        pass

    def listen(self) -> bytes:
        pass

    def process_incoming(self, data: bytes):
        pass


class TestPlant(TestCase):
    pass
