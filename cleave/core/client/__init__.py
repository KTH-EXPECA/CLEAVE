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

from .actuator import Actuator, SimpleConstantActuator, SimpleImpulseActuator
from .plant import Plant, PlantBuilder
from .sensor import Sensor, SimpleSensor
from .state import ActuatorVariable, SensorVariable, State
from ..eventloop import reactor

#: Global PlantBuilder instance
# TODO: remove Factory pattern now that we're using modular config files?
builder = PlantBuilder(reactor)

__all__ = ['builder', 'Plant',
           'Sensor', 'SimpleSensor',
           'Actuator', 'SimpleConstantActuator', 'SimpleImpulseActuator',
           'State', 'SensorVariable', 'ActuatorVariable']
