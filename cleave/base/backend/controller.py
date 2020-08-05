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
import functools
from abc import ABC, abstractmethod
from typing import Mapping

from ..util import PhyPropType


class Controller(ABC):
    @abstractmethod
    def process(self, sensor_values: Mapping[str, PhyPropType]) \
            -> Mapping[str, PhyPropType]:
        pass

    @classmethod
    def find_all_subclasses(cls):
        subcls = set(cls.__subclasses__())
        if len(subcls) == 0:
            return subcls
        else:
            return subcls.union(
                functools.reduce(lambda x, y: x.union(y),
                                 [s.find_all_subclasses() for s in subcls]))
