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
#  limitations under the License.

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from collections import Collection
from pathlib import Path
from typing import Union

from twisted.internet import task
from twisted.internet.posixbase import PosixReactorBase

from .actuator import Actuator, ActuatorArray
from .physicalsim import PhysicalSimulation
from .sensor import NoSensorUpdate, Sensor, SensorArray
from .time import PlantTicker, SimClock
from ..logging import LogLevel, Logger
from ..network.client import BaseControllerInterface
from ..recordable import CSVRecorder, NamedRecordable
from ...api.plant import State

_SCALAR_TYPES = (int, float, bool)


class PlantBuilderWarning(Warning):
    pass


class EmulationWarning(Warning):
    pass


class Plant(ABC):
    """
    Interface for all plants.
    """

    def __init__(self):
        self._logger = Logger()
        self._ticker = PlantTicker()
        self._clock = SimClock()

    @abstractmethod
    def execute(self):
        """
        Executes this plant. Depending on implementation, this method may or
        may not be asynchronous.

        Returns
        -------

        """
        pass

    @property
    @abstractmethod
    def simulation_tick_rate(self) -> int:
        """
        The update frequency of this plant in Hz. Depending on
        implementation, accessing this property may or may not be thread-safe.

        Returns
        -------
        int
            The update frequency of the plant in Hertz.

        """
        pass

    @property
    @abstractmethod
    def simulation_tick_dt(self) -> float:
        # TODO: document
        pass

    @abstractmethod
    def on_shutdown(self) -> None:
        """
        Handle shutdown stuff.
        """
        pass


class BasePlant(Plant):
    def __init__(self,
                 reactor: PosixReactorBase,
                 physim: PhysicalSimulation,
                 sensor_array: SensorArray,
                 actuator_array: ActuatorArray,
                 control_interface: BaseControllerInterface):
        super(BasePlant, self).__init__()
        self._reactor = reactor
        self._physim = physim
        self._sensors = sensor_array
        self._actuators = actuator_array
        self._control = control_interface

        # plant_timings
        # TODO: put into state wrapper class
        self._timings = NamedRecordable(
            name='PlantTimings',
            record_fields=['seq', 'start', 'end', 'tick_delta']
        )

    @property
    def simulation_tick_rate(self) -> int:
        return self._physim.tick_rate

    @property
    def simulation_tick_dt(self) -> float:
        return self._physim.tick_delta

    def _execute_emu_timestep(self, count: int) -> None:
        """
        Executes the emulation timestep. Intended use is inside a Twisted
        LoopingCall, hence why it takes a single integer parameter which
        specifies the number of calls queued up in a time interval (should
        be 1).

        Parameters
        ----------
        count

        Returns
        -------

        """

        step_start = self._clock.get_sim_time()

        # 1. get raw actuation inputs
        # 2. process actuation inputs
        # 3. advance state
        # 4. process sensor outputs
        # 5. send sensor outputs
        # TODO: check that timings are respected!
        # if count > 1:
        #     self._logger.warn('Emulation step took longer '
        #                       'than allotted time slot!', )

        control_cmds = self._control.get_actuator_values()

        actuator_outputs = self._actuators.apply_actuation_inputs(
            plant_cycle=self._ticker.total_ticks + 1,  # +1 since we haven't
            input_values=control_cmds  # called tick yet!
        )

        delta_t = self._ticker.tick()
        state_outputs = self._physim.advance_state(actuator_outputs, delta_t)

        # sensor_outputs = {}
        try:
            # this only sends if any sensors are triggered during this state
            # update, otherwise an exception is raised and caught further down.
            sensor_outputs = self._sensors.process_plant_state(
                plant_cycle=self._ticker.total_ticks,
                prop_values=state_outputs)
            self._control.put_sensor_values(sensor_outputs)
        except NoSensorUpdate:
            pass
        finally:
            self._timings.push_record(
                seq=self._ticker.total_ticks,
                start=step_start,
                end=self._clock.get_sim_time(),
                tick_delta=delta_t
            )

    def on_shutdown(self) -> None:
        """
        Called on shutdown of the framework.
        """

        # output stats on shutdown
        self._logger.warn('Shutting down plant, please wait...')

        # call simulation shutdown
        self._physim.shutdown()
        self._logger.info('Plant shutdown completed.')

    def execute(self):
        """
        Initiates the simluation of this plant.
        """

        self._logger.info('Initializing plant...')
        self._logger.warn(f'Target frequency: '
                          f'{self._physim.tick_rate} Hz')
        self._logger.warn(f'Target time step: '
                          f'{self._physim.tick_delta * 1e3:0.1f} ms')

        # callback for plant rate logging
        def _log_plant_rate():
            if self._ticker.total_ticks < self._physim.tick_rate:
                # todo: more efficient way?
                # skip first second
                return

            rate = self._ticker.get_rate()
            ticks_per_second = rate.tick_count / rate.interval_s

            ratio_expected = ticks_per_second / self._physim.tick_rate
            loglevel = LogLevel.info if ratio_expected > 0.95 else \
                LogLevel.warn if ratio_expected > 0.85 else LogLevel.error

            self._logger.emit(level=loglevel,
                              format=f'Current effective plant rate: '
                                     f'{rate.tick_count} ticks in '
                                     f'{rate.interval_s:0.3f} seconds, '
                                     f'for an average of '
                                     f'{ticks_per_second:0.3f} ticks/second.')

        # callback to wait for network before starting simloop
        def _wait_for_network_and_init():
            if not self._control.is_ready():
                # controller not ready, wait a bit
                self._logger.warn('Waiting for controller...')
                self._reactor.callLater(0.01, _wait_for_network_and_init)
            else:
                # schedule timestep
                self._logger.info('Starting simulation...')
                self._physim.initialize()
                sim_loop = task.LoopingCall \
                    .withCount(self._execute_emu_timestep)
                sim_loop.clock = self._reactor

                ticker_loop = task.LoopingCall(_log_plant_rate)
                ticker_loop.clock = self._reactor

                # have loop run slightly faster than required, as we rather
                # have the plant be a bit too fast than too slow
                # todo: parameterize the scaling factor?
                # todo: tune this
                sim_loop.start(interval=self._physim.tick_delta * 0.9)
                ticker_loop.start(interval=5)  # TODO: magic number?

        self._control.register_with_reactor(self._reactor)
        # callback for shutdown
        self._reactor.addSystemEventTrigger('after', 'shutdown',
                                            self.on_shutdown)

        self._reactor.callWhenRunning(_wait_for_network_and_init)
        self._reactor.suggestThreadPoolSize(3)  # input, output and processing
        self._reactor.run()


class CSVRecordingPlant(BasePlant):
    """
    Plant with built-in CSV recording capabilities of metrics from the  the
    physical properties and the network connection.
    """

    def __init__(self,
                 reactor: PosixReactorBase,
                 physim: PhysicalSimulation,
                 sensor_array: SensorArray,
                 actuator_array: ActuatorArray,
                 control_interface: BaseControllerInterface,
                 recording_output_dir: Path = Path('.')):
        super(CSVRecordingPlant, self).__init__(
            reactor=reactor,
            physim=physim,
            sensor_array=sensor_array,
            actuator_array=actuator_array,
            control_interface=control_interface
        )

        if not recording_output_dir.exists():
            recording_output_dir.mkdir(parents=True, exist_ok=False)
        elif not recording_output_dir.is_dir():
            raise FileExistsError(f'{recording_output_dir} exists and is not a '
                                  f'directory, aborting.')

        # TODO: factories?
        self._recorders = {
            CSVRecorder(self._timings, recording_output_dir / 'timings.csv'),
            CSVRecorder(self._control, recording_output_dir / 'client.csv'),
            CSVRecorder(self._sensors, recording_output_dir / 'sensors.csv'),
            CSVRecorder(self._actuators,
                        recording_output_dir / 'actuators.csv'),
        }

    def execute(self):
        for recorder in self._recorders:
            recorder.initialize()
        super(CSVRecordingPlant, self).execute()

    def on_shutdown(self) -> None:
        super(CSVRecordingPlant, self).on_shutdown()

        # shut down recorders
        for recorder in self._recorders:
            recorder.shutdown()


# noinspection PyAttributeOutsideInit
class PlantBuilder:
    """
    Builder for plant objects.

    This class is not meant to be instantiated by users --- a library
    singleton is provided.

    TODO: get rid of the singleton, it's not necessary at this point.
    """

    def reset(self) -> None:
        """
        Resets this builder, removing all previously added sensors,
        actuators, as well as detaching the plant state and comm client.

        Returns
        -------

        """
        self._sensors = []
        self._actuators = []
        self._controller = None
        self._plant_state = None
        self._simulation_tick_rate = 1

    def __init__(self, reactor: PosixReactorBase):
        self._reactor = reactor
        self.reset()

    def attach_sensor(self, sensor: Sensor) -> None:
        """
        Attaches a sensor to the plant under construction.

        Parameters
        ----------
        sensor
            A Sensor instance to be attached to the target plant.


        Returns
        -------

        """
        self._sensors.append(sensor)

    def attach_actuator(self, actuator: Actuator) -> None:
        """
        Attaches an actuator to the plant under construction.

        Parameters
        ----------
        actuator
            An Actuator instance to be attached to the target plant.

        Returns
        -------

        """
        self._actuators.append(actuator)

    def set_sensors(self, sensors: Collection[Sensor]) -> None:
        self._sensors = list(sensors)

    def set_actuators(self, actuators: Collection[Actuator]) -> None:
        self._actuators = list(actuators)

    def set_simulation_tick_rate(self, rate: int) -> None:
        self._simulation_tick_rate = rate

    def set_controller(self, controller: BaseControllerInterface) -> None:
        if self._controller is not None:
            warnings.warn(
                'Replacing already set controller for plant.',
                PlantBuilderWarning
            )

        self._controller = controller

    def set_plant_state(self, plant_state: State) -> None:
        """
        Sets the State that will govern the evolution of the plant.

        Note that any previously assigned State will be overwritten by this
        operation.

        Parameters
        ----------
        plant_state
            A State instance to assign to the plant.

        Returns
        -------

        """
        if self._plant_state is not None:
            warnings.warn(
                'Replacing already set State for plant.',
                PlantBuilderWarning
            )

        self._plant_state = plant_state

    def build(self, csv_output_dir: Union[str, bool]) -> Plant:
        """
        Builds a Plant instance and returns it. The actual subtype of this
        plant will depend on the previously provided parameters.

        Parameters
        ----------
        Returns
        -------
        Plant
            A Plant instance.

        """

        # TODO: raise error if missing parameters OR instantiate different
        #  types of plants?
        params = dict(
            reactor=self._reactor,
            physim=PhysicalSimulation(self._plant_state,
                                      self._simulation_tick_rate),
            sensor_array=SensorArray(
                plant_tick_rate=self._simulation_tick_rate,
                sensors=self._sensors),
            actuator_array=ActuatorArray(actuators=self._actuators),
            control_interface=self._controller
        )

        try:
            # TODO: rework
            if csv_output_dir:
                return CSVRecordingPlant(
                    recording_output_dir=Path(csv_output_dir),
                    **params
                )
            else:
                return BasePlant(**params)
        finally:
            self.reset()
