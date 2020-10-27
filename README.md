[![Documentation Status](https://readthedocs.org/projects/cleave/badge/?version=latest)](https://cleave.readthedocs.io/en/latest/?badge=latest)

CLEAVE - ControL bEnmArking serVice on the Edge: A framework for testing, benchmarking and evaluating control loop applications on the Edge, written in Python 3.8+.
---
*Note: This project is in early stages of development.*
---

## Installation for general usage
### From `pip`

*Although these instructions will eventually be the recommended way of downloading and installing the framework, they are currently a work-in-progress, and may not work yet. For failsafe ways to install the framework, see the following sections*

Set up a Python virtualenv, activate it and install the framework from `pip`:

```bash
$ virtualenv --python=python3.8 ./venv
created virtual environment CPython3.8.3.final.0-64 in 212ms
...

$ . ./venv/bin/activate
(venv) $ pip install cleave
```

Alternatively, if you already have set up a project with an associated virtualenv, you can add `cleave` to your `requirements.txt`:

```text
# example requirements.txt
...
numpy
pandas
cleave
scipy
```

```bash
(venv) pip install -Ur ./requirements.txt
```

### From the repositories

1. Clone the repository: `$ git clone git@github.com:KTH-EXPECA/CLEAVE.git`

2. In your project directory, set up a Python virtualenv and activate it:

    ```bash
    $ cd myproject/
    $ virtualenv --python=python3.8 ./venv
    created virtual environment CPython3.8.3.final.0-64 in 212ms
    ...
    
    $ . ./venv/bin/activate
   (venv) $
    ```

3. Install CLEAVE from the previously cloned repositories by pointing `pip` to the root of the CLEAVE repo:

    ```bash
    (venv) $ pip install -U /path/to/CLEAVE
    ```
    

## Setting up for development:

1. Clone the CLEAVE repository:
   ```bash
   $ git clone git@github.com:KTH-EXPECA/CLEAVE.git
   $ cd ./CLEAVE
   ```

2.  Create a Python 3.8+ virtualenv and install the development dependencies:
    
    ```bash
    $ virtualenv --python=python3.8 ./venv
    created virtual environment CPython3.8.3.final.0-64 in 212ms
    ...
    
    $ . ./venv/bin/activate
    (venv) $ pip install -Ur ./requirements.txt
    ```

3. (Optional) To build the documentation using Sphinx:

    1. Install the documentation dependencies:
    
        ```bash
        (venv) $ pip install -Ur requirements_docs.txt
        ```
    
    2. Document code using the Numpy docstring format (see below).
    
    3. Generate reStructured text files for the code using `sphinx-apidocs` from the top-level directory:
    
        ```bash
        $ sphinx-apidoc -fo docs/source . ./setup.py ./cleave/client/actuator.py ./cleave/client/sensor.py ./cleave/client/plant.py ./cleave/network/handler.py ./tests ./examples
        ```
       
       Note the exclude directives in the command, to avoid generating documentation for files such as `setup.py` and files deep within the project structure. 
    4. (Optional) To preview what the documentation will look like when published on [cleave.readthedocs.io
    ](https://cleave.readthedocs.io), build it with `GNU Make`:
    
        ```bash
        $ cd docs/
        $ make html
        ```
       
       The compiled HTML structure will be output to `docs/build`, from where it can be viewed in a browser.
       
### Running the Inverted Pendulum example implementation

Example implementations of an inverted pendulum plant and controller setup are included.

To run the server:
```bash
(venv) $ python cleave.py run-controller examples/controller_config.py
```

By default, the controller listens on UDP port 50000. This can be changed from the command line using the `--bind-port <port>` option.

To run the client:
```bash
(venv) $ python cleave.py run-plant examples/plant_config.py
```

Again, by default the plant connects to UDP port 50000 on `localhost`. This can be altered from the command line using the `--host-address <ip/hostname> <port>` option.

Both the plant and controller have additional options -- see their respective help menus for details (`--help` flag).

### Configuring the Plant and Controller

See [this file](configuring_plant_controller.md) for details.

### Code style and standards:

*When developing on this project, please configure your IDE to adhere to the following guidelines.*

The code in this repository should be [PEP8 coding style guide](https://pep8.org/) compliant, with one exception: maximum line length. 
[PEP8 specifies a maximum line length of 79 characters](https://pep8.org/#maximum-line-length), a relic of a time where widescreen monitors didn't exist. In this project, we extend the maximum line length to 120 characters.

Furthermore, code documentation in this project should follow the [Numpy docstring format as detailed here.](https://numpydoc.readthedocs.io/en/latest/format.html#docstring-standard)

Finally, every Python module in this project should include an Apache License v2.0 statement at the top:

```python
#  Copyright (c) 2020 KTH Royal Institute of Technology
#
#  Licensed under the Apache License, Version 2.0 (the 'License');
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an 'AS IS' BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#   limitations under the License.
# 
```

## License

Copyright 2020 KTH Royal Institute of Technology

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this project except in compliance with the License. A copy of the license is included in the [LICENSE](LICENSE) file.

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
