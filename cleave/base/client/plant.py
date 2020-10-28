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
from threading import RLock

from twisted.internet import threads
from twisted.internet.posixbase import PosixReactorBase
from twisted.python.failure import Failure

from .actuator import Actuator, ActuatorArray
from .sensor import NoSensorUpdate, Sensor, SensorArray
from .state import State
from .time import SimClock
from ..logging import Logger
from ..network.client import BaseControllerInterface
# from ..stats.plotting import plot_plant_metrics
# from ..stats.realtime_plotting import RealtimeTimeseriesPlotter
# from ..stats.stats import RollingStatistics
from ...base.util import PhyPropMapping

# TODO: move somewhere else maybe
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
    def update_freq_hz(self) -> int:
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
    def plant_state(self) -> State:
        """
        The State object associated with this plant. Depending on
        implementation, accessing this property may or may not be thread-safe.

        Returns
        -------
        State
            The plant State.
        """
        pass

    @abstractmethod
    def on_shutdown(self) -> None:
        """
        Handle shutdown stuff.
        """
        pass


class _BasePlant(Plant):
    def __init__(self,
                 reactor: PosixReactorBase,
                 update_freq: int,
                 state: State,
                 sensor_array: SensorArray,
                 actuator_array: ActuatorArray,
                 control_interface: BaseControllerInterface):
        super(_BasePlant, self).__init__()
        self._reactor = reactor
        self._freq = update_freq
        self._state = state
        self._sensors = sensor_array
        self._actuators = actuator_array
        self._cycles = 0
        self._control = control_interface

        self._lock = RLock()

        # save state stats, i.e., every actuator and sensor variable both
        # before and after processing
        # TODO: reimplement stats

        # stat_cols = ['timestamp']
        # for var, t in state.get_sensed_props().items():
        #     if t in _SCALAR_TYPES:
        #         stat_cols.append(f'sens_{var}_raw')
        #         stat_cols.append(f'sens_{var}_proc')
        #
        # for var, t in state.get_actuated_props().items():
        #     if t in _SCALAR_TYPES:
        #         stat_cols.append(f'act_{var}_raw')
        #         stat_cols.append(f'act_{var}_proc')
        #
        # self._stats = RollingStatistics(columns=stat_cols)

    @property
    def update_freq_hz(self) -> int:
        return self._freq

    @property
    def plant_state(self) -> State:
        return self._state

    # TODO: reimplement
    # def _record_stats(self,
    #                   timestamp: float,
    #                   act: Mapping[str, PhyPropType],
    #                   act_proc: Mapping[str, PhyPropType],
    #                   sens: Mapping[str, PhyPropType],
    #                   sens_proc: Mapping[str, PhyPropType]):
    #
    #     # helper function to defer recording of stats after a step
    #
    #     record = {'timestamp': timestamp}
    #     for var, val in act.items():
    #         record[f'act_{var}_raw'] = val
    #
    #     for var, val in act_proc.items():
    #         record[f'act_{var}_proc'] = val
    #
    #     for var, val in sens.items():
    #         record[f'sens_{var}_raw'] = val
    #
    #     for var, val in sens_proc.items():
    #         record[f'sens_{var}_proc'] = val
    #
    #     self._stats.add_record(record)

    def _emu_step(self):
        # 1. get raw actuation inputs
        # 2. process actuation inputs
        # 3. advance state
        # 4. process sensor outputs
        # 5. send sensor outputs
        act = self._control.get_actuator_values()
        proc_act = self._actuators.process_actuation_inputs(act)

        with self._lock:
            # this is always called from a separate thread so add some
            # thread-safety just in case
            sensor_raw = self._state.state_update(proc_act)
            self._cycles += 1

        # this will only send sensor updates if we actually have any,
        # since otherwise it raises an exception which will be caught in
        # the callback
        sensor_proc = {}
        try:
            sensor_proc = self._sensors.process_plant_state(sensor_raw)
            return sensor_proc
        finally:
            # TODO: reimplement
            # immediately schedule the function to record the stats
            # task.deferLater(self._reactor, 0, self._record_stats,
            #                 timestamp=time.time(),
            #                 act=act,
            #                 act_proc=proc_act,
            #                 sens=sensor_raw,
            #                 sens_proc=sensor_proc)
            pass

    @staticmethod
    def no_samples_errback(failure: Failure):
        failure.trap(NoSensorUpdate)
        # no sensor data to send, ignore
        return

    def send_samples_callback(self, sensor_samples: PhyPropMapping):
        # TODO: log!
        # send samples after a sim step
        self._control.put_sensor_values(sensor_samples)

    def _timestep(self, target_dt: float):
        # TODO: figure actual rate at runtime and adjust timing accordingly
        ti = self._clock.get_stopwatch()

        def reschedule_step_callback(*args, **kwargs):
            """
            Callback for iteratively rescheduling the next timestep after
            finishing the current one.
            """
            dt = ti.split()
            if target_dt - dt > 0:
                # TODO: fix the magic scaling factor...
                self._reactor.callLater((target_dt - dt) * 0.97,
                                        self._timestep, target_dt)
            else:
                warnings.warn(
                    'Emulation step took longer than allotted time slot!',
                    EmulationWarning)
                self._reactor.callLater(0, self._timestep, target_dt)

        # instead of using the default deferToThread method
        # this way we can pass the reactor and don't have to trust the
        # function to use the default one.
        threads.deferToThreadPool(self._reactor,
                                  self._reactor.getThreadPool(),
                                  self._emu_step) \
            .addCallback(self.send_samples_callback) \
            .addErrback(self.no_samples_errback) \
            .addCallback(reschedule_step_callback)

        # threads \
        #     .deferToThread(self._emu_step) \
        #     .addCallback(reschedule_step_callback)

    def on_shutdown(self) -> None:
        # output stats on shutdown
        self._logger.warn('Shutting down plant, please wait...')
        self._logger.info('Saving plant metrics to file...')
        # metrics = self._stats.to_pandas()
        # metrics.to_csv('./plant_metrics.csv', index=False)

        # TODO: parameterize!
        # TODO: put in a folder?
        # TODO: redesign and reimplement
        # plot_plant_metrics(
        #     metrics=metrics,
        #     sens_vars=self._state.get_sensed_props(),
        #     act_vars=self._state.get_actuated_props(),
        #     out_path='./',
        #     fname_prefix='plant'
        # )

        # call state shutdown
        self._state.on_shutdown()
        self._logger.info('Plant shutdown completed.')

    def execute(self):
        self._logger.info('Initializing plant...')
        target_dt = 1.0 / self._freq

        # callback to wait for network before starting simloop
        def _wait_for_network_and_init():
            if not self._control.is_ready():
                # controller not ready, wait a bit
                self._logger.warn('Waiting for controller...')
                self._reactor.callLater(0.01, _wait_for_network_and_init)
            else:
                # schedule timestep
                self._logger.info('Starting simulation...')
                self._reactor.callLater(0, self._timestep, target_dt)

        self._control.register_with_reactor(self._reactor)
        # callback for shutdown
        self._reactor.addSystemEventTrigger('before', 'shutdown',
                                            self.on_shutdown)

        self._reactor.callWhenRunning(_wait_for_network_and_init)
        self._reactor.suggestThreadPoolSize(3)  # input, output and processing
        self._reactor.run()


# TODO: reimplement plotting
# class _RealtimePlottingPlant(_BasePlant):
#     def __init__(self,
#                  reactor: PosixReactorBase,
#                  update_freq: int,
#                  state: State,
#                  sensor_array: SensorArray,
#                  actuator_array: ActuatorArray,
#                  control_interface: BaseControllerInterface):
#         super(_RealtimePlottingPlant, self).__init__(
#             reactor=reactor, update_freq=update_freq, state=state,
#             sensor_array=sensor_array, actuator_array=actuator_array,
#             control_interface=control_interface
#         )
#
#         props = dict(**state.get_sensed_props(), **state.get_actuated_props())
#         scalar_vars = set([var for var, t in props.items()
#                            if t in _SCALAR_TYPES])
#
#         # realtime plotter
#         # TODO: parameterize or move out of here
#         # TODO: default rate handles the rate for actuator values,
#         #  but there's gotta be a better way...
#         self._plotter = RealtimeTimeseriesPlotter(variables=scalar_vars)
#
#     def _record_stats(self,
#                       timestamp: float,
#                       act: Mapping[str, PhyPropType],
#                       act_proc: Mapping[str, PhyPropType],
#                       sens: Mapping[str, PhyPropType],
#                       sens_proc: Mapping[str, PhyPropType]):
#         super(_RealtimePlottingPlant, self)._record_stats(
#             timestamp=timestamp,
#             act=act, act_proc=act_proc,
#             sens=sens, sens_proc=sens_proc
#         )
#
#         # plot
#         self._plotter.put_sample(dict(**act_proc, **sens_proc))
#
#     def on_shutdown(self) -> None:
#         # plotter shutdown
#         self._logger.info('Please close plot window manually...')
#         self._plotter.shutdown()
#         self._plotter.join()
#         super(_RealtimePlottingPlant, self).on_shutdown()
#
#     def execute(self):
#         self._logger.info('Starting realtime plotting interface...')
#         # start plotter
#         self._plotter.start()
#         super(_RealtimePlottingPlant, self).execute()


# noinspection PyAttributeOutsideInit
class PlantBuilder:
    """
    Builder for plant objects.

    This class is not meant to be instantiated by users --- a library
    singleton is provided as cleave.client.builder.
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
        # self._comm_client = None
        self._controller = None
        self._plant_state = None

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

    def build(self, plotting: bool = False) -> Plant:
        """
        Builds a Plant instance and returns it. The actual subtype of this
        plant will depend on the previously provided parameters.

        Parameters
        ----------
        plotting:
            Whether to initialize a plant with realtime plotting capabilities.

        Returns
        -------
        Plant
            A Plant instance.

        """

        # TODO: raise error if missing parameters OR instantiate different
        #  types of plants?

        params = dict(
            reactor=self._reactor,
            update_freq=self._plant_state.update_frequency,
            state=self._plant_state,
            sensor_array=SensorArray(
                plant_freq=self._plant_state.update_frequency,
                sensors=self._sensors),
            actuator_array=ActuatorArray(actuators=self._actuators),
            control_interface=self._controller
        )

        try:
            # return _RealtimePlottingPlant(**params) \
            #     if plotting else _BasePlant(**params)
            return _BasePlant(**params)
        finally:
            self.reset()
