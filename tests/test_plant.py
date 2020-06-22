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
from typing import Any, Optional
from unittest import TestCase

from cleave.client import BaseActuationCommand, BaseActuator, BaseState, Plant


class DummyState(BaseState):
    def __init__(self):
        self.count = 0

    def advance(self, actuation: Optional[BaseActuationCommand] = None) \
            -> BaseState:
        if actuation is not None:
            change = actuation.payload
            self.count += change
            return self
        else:
            return self


class DummyActuationCommand(BaseActuationCommand):
    def __init__(self):
        super(DummyActuationCommand, self).__init__()

    @property
    def payload(self) -> Any:
        return 1


class DummyActuator(BaseActuator):

    def get_next_actuation(self) -> Optional[BaseActuationCommand]:
        return DummyActuationCommand()


class TestPlant(TestCase):
    def setUp(self) -> None:
        self._plant = Plant(
            dt=0.01,
            init_state=DummyState(),
            sensor=None,
            actuator=DummyActuator()
        )

        self._start = False
        self._pre_sim = False
        self._end = False

    def test_step(self):
        self.assertEqual(self._plant.sample_state().count, 0)
        self._plant._step()
        self.assertEqual(self._plant.sample_state().count, 1)

    def test_hooks(self):
        @self._plant.hook_start_of_step
        def _start():
            self.assertFalse(self._start)
            self.assertFalse(self._pre_sim)
            self.assertFalse(self._end)
            self._start = True

        @self._plant.hook_pre_sim
        def _pre_sim(actuation: Any):
            self.assertTrue(self._start)
            self.assertFalse(self._pre_sim)
            self.assertFalse(self._end)
            self._pre_sim = True
            self.assertIsNotNone(actuation)

        @self._plant.hook_end_of_step
        def _end():
            self.assertTrue(self._start)
            self.assertTrue(self._pre_sim)
            self.assertFalse(self._end)
            self._end = True

        self._plant._step()
