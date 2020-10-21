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
from typing import Iterator, Mapping, Set, Union

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import animation


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

            dt = 1 / self._plot_fps

            sns.set_theme(context='paper', palette='Dark2')
            with sns.color_palette('Dark2', nvars) as colors:
                # colors = list(colors)

                fig, axes = plt.subplots(nrows=nvars, sharex='all')
                axes[-1].set_xlabel('Time window [s]')
                fig.suptitle(f'Plant variables over a {self._time_window} '
                             f'second time window')

                # note the reversed inf values, this is so they will get
                # immediately replaced in the loop
                var_ranges = {v: np.array([np.inf, -np.inf])
                              for v in self._vars}
                var_lines = {}

                # assign plots to variables and initialize labels
                var_axes = {}
                for var, ax, c in zip(self._vars, axes, colors):
                    var_axes[var] = ax
                    var_lines[var], = ax.plot([], [], color=c)  # note the ","
                    ax.set_ylabel(var)
                    ax.set_xlim(-self._time_window, 0)

                fig.tight_layout()

                # generator for the data
                def _get_samples(*args, **kwargs) -> Iterator[deque]:
                    while not self._shutdown.is_set():
                        new_samples = deque()
                        try:
                            while True:
                                new_samples.append(self._sample_q.get_nowait())
                        except queue.Empty:
                            yield new_samples

                def _plot_update(new_samples: deque):
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
                        if data.size == 0:
                            continue

                        relative_x_time = data[:, 0] - time.monotonic()

                        # don't plot stuff we can't see
                        time_filter = relative_x_time >= -self._time_window
                        relative_x_time = relative_x_time[time_filter]
                        y = data[time_filter, 1]

                        if relative_x_time.size == 0:
                            # nothing to plot
                            var_lines[var].set_data([], [])
                        else:
                            # update var ranges to make plot a bit more smooth
                            old_range = var_ranges[var]
                            new_min = np.min((y.min(), old_range[0]))
                            new_max = np.max((y.max(), old_range[1]))
                            new_range = np.array([new_min, new_max])

                            if not (np.any(np.isinf(new_range))
                                    or np.any(np.isnan(new_range))) \
                                    and not np.all(np.isclose(new_range,
                                                              old_range)):
                                ax.set_ylim(new_range * 1.5)
                                ax.figure.canvas.draw()

                            var_ranges[var] = new_range
                            var_lines[var].set_data(relative_x_time, y)

                    return list(var_lines.values())

                ani = animation.FuncAnimation(fig,
                                              _plot_update,
                                              _get_samples,
                                              blit=True,
                                              interval=dt * 1e3,
                                              repeat=False)
                plt.show()

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
