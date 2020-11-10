import unittest
from typing import Any

from cleave.core.client import Actuator, SimpleActuator


class DummyDampenedActuator(Actuator):
    def __init__(self, prop_name: str, dampening: float):
        super(DummyDampenedActuator, self).__init__(prop_name)
        self._dampening = dampening

    def process_actuation(self, desired_value: Any) -> Any:
        return self._dampening * desired_value


class TestActuator(unittest.TestCase):
    act_input = 10
    damp_amount = 0.8

    def setUp(self) -> None:
        self._actuator = SimpleActuator('dummy1')
        self._dactuator = DummyDampenedActuator('dummy2',
                                                TestActuator.damp_amount)

    def test_actuators(self):
        self._actuator.apply_value(TestActuator.act_input)
        self._dactuator.apply_value(TestActuator.act_input)

        self.assertEqual(self._actuator.get_actuator_value(),
                         TestActuator.act_input)

        self.assertEqual(self._dactuator.get_actuator_value(),
                         TestActuator.act_input * TestActuator.damp_amount)
