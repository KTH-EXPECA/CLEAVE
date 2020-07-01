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

import threading
from abc import abstractmethod
from math import floor

from loguru import logger
from multiprocess.connection import Pipe

from .mproc import TimedRunnableLoop


class Sensor(TimedRunnableLoop):
    """
    Base class for a sensor capable of reading the state of a plant and
    sending it over the network to the controller.

    Thread- and process-safe.
    """

    def __init__(self, sample_freq_hz: float):
        """
        Parameters
        ----------
        sample_freq_hz
            The sampling frequency of the sensor, in Hertz.
        """
        super(Sensor, self).__init__(
            dt_ns=int(floor(1.0 / sample_freq_hz) * 1e9)
        )
        self._freq = sample_freq_hz
        self._pipe_recv, self._pipe_send = Pipe(duplex=False)

        self._lock = threading.RLock()
        self._sample = None

    def shutdown(self) -> None:
        super(Sensor, self).shutdown()
        self._pipe_recv.close()
        self._pipe_send.close()

    @property
    def sampling_freq(self) -> float:
        """
        Returns
        -------
            float
                Sampling frequency of this sensor, in Hertz.
        """
        return self._freq

    @abstractmethod
    def prepare_sample(self, sample: bytes) -> bytes:
        """
        Prepares the sampled state to be sent to the controller.

        This method should be overridden by inheriting classes, in order to,
        for instance, add noise to the state according to some internal
        parameter of the sensor.

        Parameters
        ----------
        sample
            The last sampled state of the system.

        Returns
        ----------
        bytes
            An potentially transformed or distorted copy of the sampled state.
        """
        pass

    @abstractmethod
    def send(self, payload: bytes) -> None:
        """
        Sends the passed binary payload to the controller. What "sending"
        actually means is left up to the implementing class.

        Should be implemented by inheriting classes.

        Parameters
        ----------
        payload:
            Bytes to be sent to the controller.
        """
        pass

    def _loop(self):
        with self._lock:
            sample = self._sample

        if sample is not None:
            self.send(self.prepare_sample(sample))

    def run(self) -> None:
        def _pipe_listen():
            try:
                while True:
                    data = self._pipe_recv.recv()
                    with self._lock:
                        self._sample = data
            except EOFError:
                logger.warning('Sensor got EOF from pipe.')

        threading.Thread(
            target=_pipe_listen
        ).start()
        super(Sensor, self).run()

    def update_sample(self, sample: bytes) -> None:
        self._pipe_send.send(sample)
