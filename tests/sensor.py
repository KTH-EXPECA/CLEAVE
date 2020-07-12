import unittest
from typing import Any

from cleave.client import Sensor, SimpleSensor
from cleave.client.sensor import SensorArray


class SquareValueSensor(Sensor):
    def add_noise(self, value: Any) -> Any:
        return value * value


class TestSimpleSensor(unittest.TestCase):
    input_val = 10
    input_val2 = 20

    def setUp(self) -> None:
        self.sensor = SimpleSensor(prop_name='dummy1', fs=200)
        self.sqr_sensor = SquareValueSensor(prop_name='dummy2', fs=100)
        self.array = SensorArray(plant_freq=200)

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

    def test_array(self):
        self.sensor.write_value(0)
        self.sqr_sensor.write_value(0)

        self.array.add_sensor(self.sensor)
        self.array.add_sensor(self.sqr_sensor)

        self.assertEqual(self.sensor.read_value(), 0)
        self.assertEqual(self.sqr_sensor.read_value(), 0)

        # test frequency synchronization
        # simple sensor should update every step,
        # sqr sensor should update every other step

        for i in range(10000):
            if i % 2 == 0:
                self.array.update_property_values({
                    self.sensor.measured_property_name    :
                        TestSimpleSensor.input_val,
                    self.sqr_sensor.measured_property_name:
                        TestSimpleSensor.input_val
                })
                self.assertEqual(self.sqr_sensor.read_value(),
                                 TestSimpleSensor.input_val ** 2)
                self.assertEqual(self.sensor.read_value(),
                                 TestSimpleSensor.input_val)

            else:
                self.array.update_property_values({
                    self.sensor.measured_property_name    :
                        TestSimpleSensor.input_val2,
                    self.sqr_sensor.measured_property_name:
                        TestSimpleSensor.input_val2
                })

                self.assertEqual(self.sqr_sensor.read_value(),
                                 TestSimpleSensor.input_val ** 2)
                self.assertEqual(self.sensor.read_value(),
                                 TestSimpleSensor.input_val2)
