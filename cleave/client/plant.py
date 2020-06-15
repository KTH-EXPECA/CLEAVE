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
import time
from abc import ABC, abstractmethod


class AbstractPlant(ABC):
    """
    Base class providing general functionality to represent closed-loop
    control plants.
    """

    def __init__(self, dt: float):
        self.dt = dt
        self.step_cnt = 0

    @abstractmethod
    def pre_actuate_hook(self):
        pass

    @abstractmethod
    def pre_simulate_hook(self):
        pass

    @abstractmethod
    def post_simulate_hook(self):
        pass

    @abstractmethod
    def actuate(self):
        pass

    @abstractmethod
    def simulate(self):
        pass

    def sample_system_state(self):
        # TODO
        pass

    def run(self):
        """
        Executes the simulation loop.
        """
        while True:
            # TODO: need way to shutdown
            ti = time.time()

            self.pre_actuate_hook()
            self.actuate()
            self.pre_simulate_hook()
            self.simulate()
            self.post_simulate_hook()
            self.sample_system_state()

            self.step_cnt += 1

            dt = time.time() - ti
            time.sleep(self.dt - dt)
