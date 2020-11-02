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
from typing import Optional

from twisted.internet import task
from twisted.internet.posixbase import PosixReactorBase

from .actuator import Actuator, ActuatorArray
from .sensor import NoSensorUpdate, Sensor, SensorArray
from .state import State
from .time import SimClock
from ..logging import Logger
from ..network.client import BaseControllerInterface
# from ..stats.plotting import plot_plant_metrics
# from ..stats.realtime_plotting import RealtimeTimeseriesPlotter
# from ..stats.stats import RollingStatistics
from ..sinks import PlantCSVStatCollector, Sink, SinkGroup

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


class BasePlant(Plant):
    def __init__(self,
                 reactor: PosixReactorBase,
                 state: State,
                 sensor_array: SensorArray,
                 actuator_array: ActuatorArray,
                 plant_sinks: SinkGroup,
                 client_sinks: SinkGroup,
                 control_interface: BaseControllerInterface):
        super(BasePlant, self).__init__()
        self._reactor = reactor
        self._freq = state.update_frequency
        self._target_dt = 1.0 / self._freq
        self._state = state
        self._sensors = sensor_array
        self._actuators = actuator_array
        self._cycles = 0
        self._control = control_interface

        # TODO: do something with client sinks
        self._plant_sinks = plant_sinks
        self._client_sinks = client_sinks

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
    def target_step_dt(self) -> float:
        return self._target_dt

    @property
    def plant_state(self) -> State:
        return self._state

    def _execute_emu_timestep(self, count: int) -> None:
        # 1. get raw actuation inputs
        # 2. process actuation inputs
        # 3. advance state
        # 4. process sensor outputs
        # 5. send sensor outputs
        step_start = self._clock.get_sim_time()

        # check that timings are respected!
        if count > 1:
            self._logger.warn(
                'Emulation step took longer than allotted time slot!', )

        act_cmd = self._control.get_actuator_values()

        self._actuators.apply_actuation_inputs(act_cmd)
        act_val = self._actuators.get_actuation_values()
        sensor_raw = self._state.state_update(act_val)
        self._cycles += 1

        sensor_proc = {}
        try:
            # this only sends if any sensors are triggered during this state
            # update, otherwise an exception is raised and caught further down.
            sensor_proc = self._sensors.process_plant_state(sensor_raw)
            self._control.put_sensor_values(sensor_proc)
        except NoSensorUpdate:
            pass
        finally:
            pass
            # sink plant state
            # TODO: is there a better way to do this?
            # TODO: create a namedtuple? or a function to modularize this
            # this should be a state snapshot, refactor!!
            # state_snapshot = {
            #     'sensor_values'  : {
            #         'raw'      : sensor_raw,
            #         'processed': sensor_proc
            #     },
            #     'actuator_values': {
            #         'raw'      : act_raw,
            #         'processed': act_proc
            #     },
            #     'timestamps'     : {
            #         'start': step_start,
            #         'end'  : self._clock.get_sim_time()
            #     }
            # }
            #
            # self._reactor.callLater(0, self._plant_sinks.sink, state_snapshot)

    def on_shutdown(self) -> None:
        # output stats on shutdown
        self._logger.warn('Shutting down plant, please wait...')

        # close sinks
        self._plant_sinks.on_end()
        self._client_sinks.on_end()

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
        self._logger.warn(f'Target DT: {self._target_dt} s')

        # callback to wait for network before starting simloop
        def _wait_for_network_and_init():
            if not self._control.is_ready():
                # controller not ready, wait a bit
                self._logger.warn('Waiting for controller...')
                self._reactor.callLater(0.01, _wait_for_network_and_init)
            else:
                # schedule timestep
                self._logger.info('Starting simulation...')
                loop = task.LoopingCall \
                    .withCount(self._execute_emu_timestep)
                loop.clock = self._reactor
                loop.start(self._target_dt)

        self._control.register_with_reactor(self._reactor)
        # callback for shutdown
        self._reactor.addSystemEventTrigger('before', 'shutdown',
                                            self.on_shutdown)

        # start sinks
        self._plant_sinks.on_start()
        self._client_sinks.on_start()

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
        self._plant_sinks = []
        self._client_sinks = []
        # self._comm_client = None
        self._controller = None
        self._plant_state = None

    def __init__(self, reactor: PosixReactorBase):
        self._reactor = reactor
        self.reset()

    def attach_plant_sink(self, sink: Sink) -> None:
        self._plant_sinks.append(sink)

    def attach_client_sink(self, sink: Sink) -> None:
        self._plant_sinks.append(sink)

    def set_plant_sinks(self, sinks: Collection[Sink]) -> None:
        self._plant_sinks = list(sinks)

    def set_client_sinks(self, sinks: Collection[Sink]) -> None:
        self._client_sinks = list(sinks)

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

    def build(self,
              plant_csv_output_path: Optional[str]) -> Plant:
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

        # TODO: put in default config? no?
        if plant_csv_output_path is not None:
            self._plant_sinks.append(
                PlantCSVStatCollector(
                    self._plant_state.get_sensed_props(),
                    self._plant_state.get_actuated_props(),
                    plant_csv_output_path
                )
            )

        params = dict(
            reactor=self._reactor,
            state=self._plant_state,
            sensor_array=SensorArray(
                plant_freq=self._plant_state.update_frequency,
                sensors=self._sensors),
            actuator_array=ActuatorArray(actuators=self._actuators),
            plant_sinks=SinkGroup(name='PhysicalPlant',
                                  sinks=self._plant_sinks),
            client_sinks=SinkGroup(name='ControllerClient',
                                   sinks=self._plant_sinks),
            control_interface=self._controller
        )

        try:
            # return _RealtimePlottingPlant(**params) \
            #     if plotting else _BasePlant(**params)
            return BasePlant(**params)
        finally:
            self.reset()
