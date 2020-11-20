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
from typing import Mapping, Union

#: This module contains miscellaneous API components.

#: Type of properties that can be handled by sensors and actuators.
PhyPropType = Union[int, float, bool]
# TODO: eventually extend to array types
PhyPropMapping = Mapping[str, PhyPropType]
