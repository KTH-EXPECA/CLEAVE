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
import sys
import time
from collections import deque
from multiprocessing import Event, Process, Queue
from typing import Mapping, Set, Union

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


class RealtimeTimeseriesPlotter(Process):
    def __init__(self,
                 variables: Set[str],
                 plot_fps: int = 24,
                 time_window_s: float = 30.0):
        super(RealtimeTimeseriesPlotter, self).__init__()

        # TODO parameterize in plant building routine!

        self._vars = variables
        self._time_window = time_window_s
        self._sample_q = Queue()
        self._shutdown = Event()
        self._plot_fps = plot_fps

    def put_sample(self, sample: Mapping[str, Union[float, int]]):
        self._sample_q.put((time.monotonic(), sample))

    def shutdown(self):
        self._shutdown.set()

    def run(self) -> None:
        try:
            # set up figure, one plot per variable
            nvars = len(self._vars)

            # time windows
            # TODO: implicit maximum sample rate is 1kHz, should be
            #  parameterized somehow somewhere
            windows = {v: deque(maxlen=int(self._time_window * 1000))
                       for v in self._vars}

            var_maxs = {}
            var_mins = {}

            dt = 1 / self._plot_fps

            sns.set_theme(context='paper', palette='Dark2')
            with sns.color_palette('Dark2', nvars) as colors:
                # colors = list(colors)

                fig, axes = plt.subplots(nrows=nvars, sharex='all')
                plt.ion()
                plt.show()

                # assign plots to variables and initialize labels
                var_axes = {}
                for var, ax in zip(self._vars, axes):
                    var_axes[var] = ax
                    ax.set_ylabel(var)

                while not self._shutdown.is_set():
                    ti = time.monotonic()
                    # get samples from queue
                    new_samples = deque()
                    try:
                        while True:
                            new_samples.append(self._sample_q.get_nowait())
                    except queue.Empty:
                        pass

                    for timestamp, sample in new_samples:
                        # append samples to windows
                        for var, value in sample.items():
                            try:
                                windows[var].append((timestamp, value))
                            except KeyError:
                                pass

                    # all windows have been updated, plot
                    for var, c in zip(self._vars, colors):
                        ax = var_axes[var]

                        data = np.array(list(windows[var]))
                        relative_x_time = data[:, 0] - np.max(data[:, 0])

                        # don't plot stuff we can't see
                        time_filter = relative_x_time >= -self._time_window
                        relative_x_time = relative_x_time[time_filter]
                        y = data[time_filter, 1]

                        # update var ranges to make plot a bit more smooth
                        var_maxs[var] = np.max((y.max(),
                                                var_maxs.get(var, -np.inf)))
                        var_mins[var] = np.min((y.min(),
                                                var_mins.get(var, np.inf)))

                        ax.clear()
                        sns.lineplot(x=relative_x_time, y=y, color=c, ax=ax)
                        ax.set_xlim(-self._time_window, 0)
                        ax.set_ylim(var_mins[var] * 1.5, var_maxs[var] * 1.5)
                        ax.set_ylabel(var)

                    axes[-1].set_xlabel('Time window [s]')
                    plt.draw()
                    plt.pause(max(dt - (time.monotonic() - ti), 1e-3))

        except Exception as e:
            print(e, file=sys.stderr)
            return


class NullPlotter(RealtimeTimeseriesPlotter):
    def put_sample(self, sample: Mapping[str, Union[float, int]]):
        pass

    def run(self) -> None:
        pass

    def start(self) -> None:
        pass

    def shutdown(self):
        pass
