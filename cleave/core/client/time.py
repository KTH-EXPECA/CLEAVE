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

import time
from typing import Any, Callable, NamedTuple


class TimingResult(NamedTuple):
    start: float
    end: float
    duration: float
    results: Any


class SimClock:
    """
    This class provides consistent simulation timing measurements.
    """

    def __init__(self):
        # initial timestamps
        t0 = time.monotonic()
        self._ti_systime = time.time()
        t1 = time.monotonic()

        # the following math is to approximate the simultaneous initialization
        # of the monotonic time and system time
        self._ti = t0 + ((t1 - t0) / 2.0)

    def get_sim_time(self) -> float:
        """
        Returns
        -------
            A float representing the elapsed time in seconds since the
            initialization of this clock.
        """
        return time.monotonic() - self._ti

    def get_adjusted_realtime(self) -> float:
        """
        Returns
        -------
            A float representing the elapsed time since the UNIX Epoch,
            adjusted for monotonicity.
        """
        return self._ti_systime + self.get_sim_time()

    def time_subroutine(self, fn: Callable[[Any], Any],
                        *args, **kwargs) -> TimingResult:
        """
        Times the execution of a function with respect to this clock.

        Parameters
        ----------
        fn
            Function to be timed.
        args
            Args to pass to the timed function.
        kwargs
            Kwargs to pass to the timed function.

        Returns
        -------
            A TimingResult object containing the start and end timestamps of
            the function call, the duration of the function call in seconds
            and the results of the call.

        """
        ti = self.get_sim_time()
        results = fn(*args, **kwargs)
        tf = self.get_sim_time()

        return TimingResult(ti, tf, tf - ti, results)
