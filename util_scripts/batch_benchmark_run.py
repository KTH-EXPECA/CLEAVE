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
import signal
import subprocess
import time
from pathlib import Path

delays = (0, 4, 8, 16, 32, 64, 128)
env = dict(os.environ)
env['CLEAVE_DURATION'] = '15m'

# add qdisc and reload
subprocess.run(
    [
        'sudo',
        'tc',
        'qdisc',
        'add',
        'dev',
        'lo',
        'root',
        'netem',
        'delay',
        f'0ms'
    ]
)

for d in delays:
    print(f'Benchmarking with delay {d}ms')
    # set up loopback delays
    if d > 0:
        subprocess.run(
            [
                'sudo',
                'tc',
                'qdisc',
                'change',
                'dev',
                'lo',
                'root',
                'netem',
                'delay',
                f'{d // 2}ms'
            ]
        )

    output_dir = Path(f'./benchmarks/{d}ms_delay')
    output_dir.mkdir(parents=True, exist_ok=True)
    env['OUTPUT_DIR'] = str(output_dir)

    controller = subprocess.Popen(
        [
            'python',
            'cleave.py',
            '-vvvvv',
            '--file-log',
            str(output_dir / 'controller.log'),
            'run-controller',
            './experiment_setup/controller/config.py'
        ],
        cwd=os.getcwd(),
        env=env
    )

    # allow controller to warmup
    time.sleep(3)

    # run the plant
    subprocess.run(
        [
            'python',
            'cleave.py',
            '-vvvvv',
            '--file-log',
            str(output_dir / 'plant.log'),
            'run-plant',
            './experiment_setup/plant/config.py'
        ],
        cwd=os.getcwd(),
        env=env
    )

    controller.send_signal(sig=signal.SIGINT)
    controller.wait()

# reset tc
subprocess.run(
    [
        'sudo',
        'tc',
        'qdisc',
        'del',
        'dev',
        'lo',
        'root'
    ]
)
# done!
