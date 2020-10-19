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
import queue
from collections import deque
from multiprocessing import Event, Process, Queue
from typing import Mapping, Union

import matplotlib.pyplot as plt
import numpy as np


class RealtimeTimeseriesPlotter(Process):
    def __init__(self,
                 vars_sampling_rate: Mapping[str, int],
                 time_window_s: float = 15.0):
        super(RealtimeTimeseriesPlotter, self).__init__()
        self._vars = set(vars_sampling_rate.keys())
        self._var_rates = vars_sampling_rate
        self._time_window = time_window_s
        self._sample_q = Queue()
        self._shutdown = Event()

    def put_sample(self, sample: Mapping[str, Union[float, int]]):
        self._sample_q.put(sample)

    def shutdown(self):
        self._shutdown.set()

    def run(self) -> None:
        try:
            # set up figure, one plot per variable
            nvars = len(self._vars)
            smpls_per_wndw = {
                var: int(rate * self._time_window) for var, rate in
                self._var_rates.items()
            }

            fig, axes = plt.subplots(nrows=nvars, sharex='all')
            plt.ion()
            plt.show()

            axes[-1].set_xlabel('Time window [s]')

            # assign plots to variables and initialize labels
            var_axes = {}
            for var, ax in zip(self._vars, axes):
                var_axes[var] = ax
                ax.set_ylabel(var)

            # time windows
            windows = {v: deque(maxlen=count)
                       for v, count in smpls_per_wndw.items()}
            x_time = {v: np.linspace(0, self._time_window,
                                     endpoint=True, num=count)
                      for v, count in smpls_per_wndw.items()}

            while not self._shutdown.is_set():
                # get samples from queue
                new_samples = []
                try:
                    while True:
                        new_samples.append(self._sample_q.get_nowait())
                except queue.Empty:
                    pass

                for sample in new_samples:
                    # append samples to windows
                    for var, value in sample.items():
                        try:
                            windows[var].append(value)
                        except KeyError:
                            pass

                # all windows have been updated, plot
                for var in self._vars:
                    ax = var_axes[var]

                    data = list(windows[var])
                    n_points = len(data)
                    x = x_time[var][:n_points]

                    ax.clear()
                    ax.plot(x, data)
                    ax.set_xlim(0, self._time_window)
                    ax.set_ylabel(var)

                plt.draw()
                plt.pause(1 / 25)

        except Exception as e:
            print(e)
            raise e


class NullPlotter(RealtimeTimeseriesPlotter):
    def put_sample(self, sample: Mapping[str, Union[float, int]]):
        pass

    def run(self) -> None:
        pass

    def start(self) -> None:
        pass

    def shutdown(self):
        pass
