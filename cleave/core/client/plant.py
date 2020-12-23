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

from abc import ABC
from collections import Collection
from pathlib import Path

import pytimeparse
from twisted.internet import task
from twisted.internet.defer import Deferred
from twisted.internet.posixbase import PosixReactorBase
from twisted.internet.task import LoopingCall
from twisted.python.failure import Failure

from .actuator import ActuatorArray
from .physicalsim import PhysicalSimulation
from .sensor import SensorArray
from ..logging import LogLevel, Logger
from ..network.client import BaseControllerInterface
from ..recordable import CSVRecorder
from ...api.plant import Actuator, Sensor, UnrecoverableState


class Plant(ABC):
    """
    Interface for all plants.
    """

    def __init__(self,
                 tick_dt: float):
        self._logger = Logger()
        self._tick_dt = tick_dt

    def set_up(self,
               duration: str,
               reactor: PosixReactorBase) -> Deferred:
        duration_sec = pytimeparse.parse(duration)
        sim_loop = task.LoopingCall.withCount(self.tick)

        def timed_shutdown():
            self._logger.warn(f'Emulation timeout reached ({duration}).')
            sim_loop.stop()

        def clean_shutdown(sim_loop: LoopingCall) -> Deferred:
            self._logger.info('Plant loop shut down cleanly.')
            return task.deferLater(reactor, 0, self.on_shutdown)

        def err_shutdown(fail: Failure) -> Deferred:
            self._logger.error('Plant tick loop aborted with error!')
            try:
                self.on_tick_error(fail)
            except:
                self._logger.error('Exception in simulation loop.')
                self._logger.error(f'\n{fail.getTraceback()}')
            finally:
                return task.deferLater(reactor, 0, self.on_shutdown)

        def start_loop(*args, **kwargs):
            # schedule tick loops
            self._logger.info('Scheduling Plant ticks...')
            sim_loop_deferred = sim_loop.start(interval=self._tick_dt)
            sim_loop_deferred.addCallback(clean_shutdown)
            sim_loop_deferred.addErrback(err_shutdown)
            return sim_loop_deferred

        def init():
            self._logger.info('Initializing Plant emulation.')
            self._logger.info(f'Target duration: {duration} ({duration_sec} '
                              f'seconds).')
            self.on_init()

        d_chain = task.deferLater(reactor, 0, init)
        d_chain.addCallback(start_loop)

        # set up shutdown signal
        task.deferLater(reactor, duration_sec, timed_shutdown)

        return d_chain

    def tick(self, missed_count: int):
        pass

    def on_tick_error(self, fail: Failure) -> None:
        fail.trap()

    def on_init(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    @property
    def simulation_tick_rate(self) -> float:
        return 1 / self._tick_dt

    @property
    def simulation_tick_dt(self) -> float:
        return self._tick_dt


class BasePlant(Plant):
    def __init__(self,
                 physim: PhysicalSimulation,
                 sensors: Collection[Sensor],
                 actuators: Collection[Actuator],
                 control_interface: BaseControllerInterface):
        super(BasePlant, self).__init__(physim.target_tick_delta)
        self._physim = physim
        self._control = control_interface

        # TODO: needs to be moved into base class
        self._ticker_loop = task.LoopingCall(self._log_plant_rate_callback)

        self._sensors = SensorArray(
            sensors=sensors,
            plant_tick_rate=self._physim.target_tick_rate,
            control=self._control
        )

        self._actuators = ActuatorArray(
            actuators=actuators,
            control=self._control
        )

    def on_init(self) -> None:
        """
        Sets up the simulation of this plant
        """

        self._logger.info('Initializing plant...')
        self._logger.warn(f'Target frequency: '
                          f'{self._physim.target_tick_rate} Hz')
        self._logger.warn(f'Target time step: '
                          f'{self._physim.target_tick_delta * 1e3:0.1f} ms')
        self._physim.initialize()
        self._ticker_loop.start(interval=5)  # TODO: magic number?

    def tick(self, missed_count: int) -> None:
        """
        Executes the emulation timestep. Intended use is inside a Twisted
        LoopingCall, hence why it takes a single integer parameter which
        specifies the number of calls queued up in a time interval (should
        be 1).

        Parameters
        ----------
        missed_count

        Returns
        -------

        """
        # 1. get raw actuation inputs
        # 2. process actuation inputs
        # 3. advance state
        # 4. process sensor outputs
        # 5. send sensor outputs
        # TODO: check that timings are respected!
        # if count > 1:
        #     self._logger.warn('Emulation step took longer '
        #                       'than allotted time slot!', )

        actuator_outputs = self._actuators.get_actuation_inputs()
        state_outputs = self._physim.advance_state(actuator_outputs)
        # sensor_outputs = {}
        # this only sends if any sensors are triggered during this state update
        self._sensors.process_and_send_samples(prop_values=state_outputs)

    def on_tick_error(self, fail: Failure) -> None:
        fail.trap(UnrecoverableState)
        import datetime
        # called after the state raises an UnrecoverableState
        # log the error and shutdown
        self._logger.error('Simulation has reached an unrecoverable state. '
                           'Aborting.')

        timestamp = f'{datetime.datetime.now():%Y%m%d_%H%M%S.%f}'
        err_log_path = Path(f'./errlog_{timestamp}.json')
        with err_log_path.open('w') as fp:
            print(fail.getErrorMessage(), file=fp)

        self._logger.error(
            'Details of variables which failed sanity checks '
            f'have been output to {err_log_path.resolve()}')

    def on_shutdown(self) -> None:
        """
        Called on shutdown of the plant.
        """

        self._logger.warn('Shutting down plant, please wait...')
        self._ticker_loop.stop()

        # call simulation shutdown
        self._physim.shutdown()
        self._logger.info('Plant shutdown completed.')

    def _log_plant_rate_callback(self):
        # callback for plant rate logging
        # TODO: put into PhySim class
        if self._physim.tick_count < self._physim.target_tick_rate:
            # todo: more efficient way?
            # skip first second
            return

        rate = self._physim.ticker.get_rate()
        ticks_per_second = rate.tick_count / rate.interval_s

        ratio_expected = ticks_per_second / self._physim.target_tick_rate
        loglevel = LogLevel.info if ratio_expected > 0.95 else \
            LogLevel.warn if ratio_expected > 0.85 else LogLevel.error

        self._logger.emit(level=loglevel,
                          format=f'Current effective plant rate: '
                                 f'{rate.tick_count} ticks in '
                                 f'{rate.interval_s:0.3f} seconds, '
                                 f'for an average of '
                                 f'{ticks_per_second:0.3f} ticks/second.')


class CSVRecordingPlant(BasePlant):
    """
    Plant with built-in CSV recording capabilities of metrics from the  the
    physical properties and the network connection.
    """

    def __init__(self,
                 physim: PhysicalSimulation,
                 sensors: Collection[Sensor],
                 actuators: Collection[Actuator],
                 control_interface: BaseControllerInterface,
                 recording_output_dir: Path = Path('.')):
        super(CSVRecordingPlant, self).__init__(
            physim=physim,
            sensors=sensors,
            actuators=actuators,
            control_interface=control_interface
        )

        if not recording_output_dir.exists():
            recording_output_dir.mkdir(parents=True, exist_ok=False)
        elif not recording_output_dir.is_dir():
            raise FileExistsError(f'{recording_output_dir} exists and is not a '
                                  f'directory, aborting.')

        # TODO: factories?
        self._recorders = {
            CSVRecorder(self._physim, recording_output_dir, 'simulation'),
            # CSVRecorder(self._control, recording_output_dir, 'client'),
            CSVRecorder(self._sensors, recording_output_dir, 'sensors'),
            CSVRecorder(self._actuators, recording_output_dir, 'actuators'),
        }

    def on_init(self) -> None:
        super(CSVRecordingPlant, self).on_init()
        for recorder in self._recorders:
            recorder.initialize()

    def on_shutdown(self) -> None:
        # shut down recorders
        for recorder in self._recorders:
            recorder.shutdown()

        super(CSVRecordingPlant, self).on_shutdown()
