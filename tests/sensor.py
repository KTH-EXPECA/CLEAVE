import unittest
from typing import Dict

from cleave.core.client import Sensor, PhyPropType, SimpleSensor
from cleave.core.client import SensorArray
from cleave.core.network import CommClient


class SquareValueSensor(Sensor):
    def process_sample(self, value: PhyPropType) -> PhyPropType:
        return value * value


class DummyCommClient(CommClient):
    def __init__(self):
        self.prop_values = {}

    def connect(self):
        pass

    def disconnect(self):
        pass

    def send_raw_bytes(self, data: bytes):
        pass

    def recv_raw_bytes(self) -> bytes:
        pass

    def send_sensor_values(self, prop_values: Dict[str, PhyPropType]):
        self.prop_values = prop_values


class TestSimpleSensor(unittest.TestCase):
    input_val = 10
    input_val2 = 20

    def setUp(self) -> None:
        self.sensor = SimpleSensor(prop_name='dummy1', fs=200)
        self.sqr_sensor = SquareValueSensor(prop_name='dummy2', fs=100)
        self.comm = DummyCommClient()
        self.array = SensorArray(plant_freq=200, comm=self.comm)

    def test_process(self):
        self.assertEqual(
            TestSimpleSensor.input_val,
            self.sensor.process_sample(TestSimpleSensor.input_val)
        )

        self.assertEqual(
            TestSimpleSensor.input_val ** 2,
            self.sqr_sensor.process_sample(TestSimpleSensor.input_val)
        )

    def test_array(self):
        self.array.add_sensor(self.sensor)
        self.array.add_sensor(self.sqr_sensor)

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
                values = self.comm.prop_values
                self.assertEqual(values[self.sqr_sensor.measured_property_name],
                                 TestSimpleSensor.input_val ** 2)
                self.assertEqual(values[self.sensor.measured_property_name],
                                 TestSimpleSensor.input_val)

            else:
                self.array.update_property_values({
                    self.sensor.measured_property_name    :
                        TestSimpleSensor.input_val2,
                    self.sqr_sensor.measured_property_name:
                        TestSimpleSensor.input_val2
                })

                values = self.comm.prop_values
                self.assertRaises(KeyError,
                                  lambda: values[
                                      self.sqr_sensor.measured_property_name])
                self.assertEqual(values[self.sensor.measured_property_name],
                                 TestSimpleSensor.input_val2)
