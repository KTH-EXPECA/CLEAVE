# CLEAVE CLIENT
---

This repository contains the code for the CLEAVE client software for emulating networked control systems. The expectation is that this will be run on a Raspberry Pi or similar low-powered hardware. The code is written in python3, and uses the packages numpy, scipy, numba and line_profiler. All these packages are installable directly using pip (pip install numpy scipy numba line_profiler).

python simulator.py [-b Backend IP Address:Backend UDP Port number] [-c Client UDP Port number:Client IP Address] [-t simulation_time] [--env_M mass of the cart] [--env_m mass of the pendulum] [env_I moment of inertia of the pendulum] [--env_l length of the pendulum] [--env_bc coefficient of friction of the cart] [--env_bp coefficient of friction of the pendulum] [--env_g acceleration due to gravity]

## License

Copyright 2020 KTH Royal Institute of Technology

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this project except in compliance with the License. A copy of the license is included in the [LICENSE](LICENSE) file.

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
