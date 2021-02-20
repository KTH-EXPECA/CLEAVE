#!/usr/bin/env python3
#  Copyright (c) 2021 KTH Royal Institute of Technology
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
import os
import shutil
import signal
import subprocess
import uuid
from pathlib import Path
from threading import Condition, Event

import click

_run_cond = Condition()
_run = Event()

_compose_prefix = \
    '''
version: "3"
services:
    '''

_compose_service_template = \
    '''
  controller_{ctrl_index:02d}:
    image: molguin/cleave:cleave
    ports:
      - 500{ctrl_index:02d}:50000
    volumes:
      - /tmp/cleave/controller_{ctrl_index:02d}:/output:rw
    entrypoint: "cleave -vvvvv run-controller \
                /CLEAVE/experiment_setup/controller/config.py"
    '''


def _sig_handle(signum, frame):
    with _run_cond:
        _run.clear()
        _run_cond.notify_all()


@click.command()
@click.argument('num-controllers', type=int)
def main(num_controllers: int):
    # make a temp dir to run docker-compose from
    tmp_dir = Path(f'/tmp/{uuid.uuid4()}')
    tmp_dir.mkdir(parents=True, exist_ok=False)

    out = _compose_prefix
    for i in range(num_controllers):
        out += _compose_service_template.format(ctrl_index=i)

    with (tmp_dir / 'docker-compose.yml').open('w') as fp:
        print(out, file=fp)

    os.chdir(tmp_dir.resolve())
    subprocess.run(['docker-compose', 'up', '-d'])
    print(f'Spawned {num_controllers} controllers...')
    print('Press Ctrl-C to shutdown.')
    signal.signal(signal.SIGINT, _sig_handle)
    _run.set()

    with _run_cond:
        while _run.is_set():
            _run_cond.wait()

    subprocess.run(['docker-compose', 'kill', '-s', 'SIGINT'])
    shutil.rmtree(tmp_dir)


if __name__ == '__main__':
    main()
