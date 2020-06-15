#  Copyright (c) 2020.  Copyright 2020 KTH Royal Institute of Technology
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this project except in compliance with the License. A copy of the license is included in the LICENSE file.
#
#  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

class Environment:
    M = 0.5  # Mass of the cart (kg)
    m = 0.2  # Mass of the inverted pendulum (kg)
    I = 0.006  # Moment of inertia of the inverted pendulum (kg-m^2)
    l = 0.3  # Length of the pendulum (m)
    bc = 0.1  # Coefficient of friction for the cart
    bp = 0.012  # Coefficient of friction for the pendulum
    g = 9.81  # Acceleration due to gravity (m/s^2)
