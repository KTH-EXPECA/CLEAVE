[![Documentation Status](https://readthedocs.org/projects/cleave/badge/?version=latest)](https://cleave.readthedocs.io/en/latest/?badge=latest)

# CLEAVE - ControL bEnmArking serVice on the Edge

A framework for testing, benchmarking and evaluating control loop applications on the Edge, written in Python 3.8+.

*Note: This project is in early stages of development.*


CLEAVE is part of the [ExPECA](https://www.jamesgross.org/research/expeca/) research project at [KTH Royal Institute of Technology](https://kth.se). It aims at providing a powerful and flexible platform for the study of networked control systems, particularly on Edge Computing architectures.

## Documentation

Please see our documentation online at [cleave.readthedocs.io]( https://cleave.readthedocs.io/en/latest/).

### Building Docker images:

Local Docker images can be built using the Makefile (requires Docker and Docker Buildx, see https://docs.docker.com/build/architecture/).
Note that we use multi-stage builds to make rebuilds faster, see https://docs.docker.com/build/building/multi-stage/; the `base` stage only needs to be built once.

To build for a specific architecture (e.g. ARM64):

```bash
$ make base-arm64
$ make cleave-arm64
```

To build all images and architectures:

```bash
$ make all
```

## License

Copyright 2020 KTH Royal Institute of Technology

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this project except in compliance with the License. A copy of the license is included in the [LICENSE](LICENSE) file.

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
