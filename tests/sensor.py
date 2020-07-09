import unittest
from typing import Any

from cleave.client import Sensor, SimpleSensor


class SquareValueSensor(Sensor):
    def add_noise(self, value: Any) -> Any:
        return value * value


class TestSimpleSensor(unittest.TestCase):
    input_val = 10

    def setUp(self) -> None:
        self.sensor = SimpleSensor(prop_name='dummy1', fs=100)
        self.sqr_sensor = SquareValueSensor(prop_name='dummy2', fs=100)

    def test_read_write(self):
        self.sensor.write_value(TestSimpleSensor.input_val)
        self.sqr_sensor.write_value(TestSimpleSensor.input_val)

        self.assertEqual(
            TestSimpleSensor.input_val,
            self.sensor.read_value()
        )

        self.assertEqual(
            TestSimpleSensor.input_val ** 2,
            self.sqr_sensor.read_value()
        )
