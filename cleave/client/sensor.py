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

from __future__ import annotations

from abc import ABC, abstractmethod
from multiprocessing import Event, Process, RLock
from typing import Any, Callable, Optional

from loguru import logger

from . import BaseState, utils
from ..network.connection import UDPConnection


class BaseSensor(ABC, Process):
    """
    Base class for a sensor capable of reading the state of a plant and
    sending it over the network to the controller.

    Thread- and process-safe.
    """

    def __init__(self, sample_freq: float):
        """
        Parameters
        ----------
        sample_freq
            The sampling frequency of the sensor, in Hertz.
        """
        super(BaseSensor, self).__init__()
        self._sample = None
        self._lock = RLock()
        self._freq = sample_freq
        self._ts = 1.0 / sample_freq
        self._shutdown_event = Event()
        self._shutdown_event.set()

        self._sampling_hooks = utils.HookCollection()
        self._post_send_hooks = utils.HookCollection()

    def shutdown(self):
        """
        Shut down this sensor.
        """
        self._shutdown_event.set()

    @property
    def sampling_freq(self) -> float:
        """
        Returns
        -------
            float
                Sampling frequency of this sensor, in Hertz.
        """
        with self._lock:
            return self._freq

    @sampling_freq.setter
    def sampling_freq(self, value: float):
        with self._lock:
            self._freq = value
            self._ts = 1.0 / value

    @property
    def sample(self) -> Optional[Any]:
        """
        Returns
        -------
        Optional[Any]
            Most recently sampled state of the plant, or None if no sampling
            has yet occurred.
        """
        with self._lock:
            return self._sample

    @sample.setter
    def sample(self, value: Any):
        with self._lock:
            self._sample = value

    def hook_sampling(self, fn: Callable[[], ...]):
        """
        Register a callable to be called at the beginning of each
        sample-then-send step.
        This callable should take no arguments.

        The intended use pattern for this method is as a decorator.

        Parameters
        ----------
        fn
            Callable to be invoked at the start of sampling interval.
        """
        self._sampling_hooks.add(fn)

    def hook_post_send(self, fn: Callable[[Any], ...]):
        """
        Register a callable to be called immediately after sending the
        sampled state to the controller. This callable should take a single
        argument which holds whatever was sent to the controller.

        The intended use pattern for this method is as a decorator.

        Parameters
        ----------
        fn
            Callable to be invoked immediately after sending something to the
            controller.
        """
        self._post_send_hooks.add(fn)

    @abstractmethod
    def prepare_state(self, state: BaseState) -> bytes:
        """
        Prepares the sampled state to be sent to the controller.

        This method should be overridden by inheriting classes, in order to,
        for instance, add noise to the state according to some internal
        parameter of the sensor. Additionally, this method needs to return a
        bytes object representation of the state.

        Parameters
        ----------
        state
            The last sampled state of the system.
        """
        pass

    @abstractmethod
    def send(self, payload: bytes) -> Any:
        """
        Sends the passed binary payload to the controller. What "sending"
        actually means is left up to the implementing class.

        Should be implemented by inheriting classes, and return whatever was
        sent.

        Parameters
        ----------
        payload:
            Bytes to be sent to the controller.
        """
        pass

    def _prepare_and_send_state(self):
        """
        Helper function to encapsulate the sensor sampling procedure.
        """

        self._sampling_hooks.call()

        sample = self.prepare_state(self.state)
        sent = self.send(sample)

        self._post_send_hooks.call(sent)

    def start(self) -> None:
        if self._shutdown_event.is_set():
            super(BaseSensor, self).start()

    def run(self) -> None:
        """
        Executes the sampling loop.
        """
        self._shutdown_event.clear()
        try:
            utils.execute_periodically(
                fn=BaseSensor._prepare_and_send_state,
                period=self._ts,
                args=(self,),
                shutdown_flag=self._shutdown_event
            )
        except Exception as e:
            # TODO: descriptive exceptions
            logger.opt(exception=e).error('Caught exception in sensor '
                                          'sampling loop!', enqueue=True)
            self.shutdown()


class UDPSensor(ABC, BaseSensor, UDPConnection):
    # TODO
    pass
