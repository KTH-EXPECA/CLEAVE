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
import subprocess

import click


@click.command()
@click.argument('host-addr', type=str)
@click.argument('num-plants', type=int)
@click.option('-o', '--output-dir',
              default='/home/pi/cleave',
              show_default=True,
              type=click.Path(exists=False,
                              file_okay=False,
                              dir_okay=True))
@click.option('--plant-addr-template',
              type=str, default='192.168.1.2{:02d}', show_default=True)
@click.option('--cleave_docker_img',
              type=str, default='molguin/cleave:cleave', show_default=True)
@click.option('-d', '--exp-duration',
              type=str, default='35m', show_default=True)
@click.option('-u', '--rpi-user',
              type=str, default='pi', show_default=True)
@click.option('-p', '--rpi-passwd',
              type=str, default='raspberry', show_default=True)
def main(host_addr: str,
         num_plants: int,
         output_dir: str = './cleave',
         plant_addr_template: str = '192.168.1.2{:02d}',
         cleave_docker_img: str = 'molguin/cleave:cleave',
         exp_duration: str = '35m',
         rpi_user: str = 'pi',
         rpi_passwd: str = 'raspberry'):
    # prepare plant addresses
    addresses = [plant_addr_template.format(i) for i in range(num_plants)]

    env = dict(os.environ)
    env['DEBIAN_FRONTEND'] = 'noninteractive'

    # make sure all plants have the necessary image
    procs = [subprocess.Popen(
        [
            'sshpass', '-p', rpi_passwd,
            'ssh', '-oPubkeyAuthentication=no', '-oPasswordAuthentication=yes',
            f'{rpi_user}@{addr}', '--',
            'docker', 'pull', cleave_docker_img
        ],
        env=env
    ) for addr in addresses]

    for p in procs:
        p.wait()

    print('All images pulled and ready.')
    print('Starting experiment in...')
    for t in range(5, 0, -1):
        print(f'\r{t}', end='')
    print()

    # run the experiment
    # each plant connects to a different port on the host
    procs = [subprocess.Popen(
        [
            'sshpass', '-p', rpi_passwd,
            'ssh', '-oPubkeyAuthentication=no', '-oPasswordAuthentication=yes',
            f'{rpi_user}@{addr}', '--',
            'docker', 'run', '--rm', '-d',
            '-e', f'CLEAVE_DURATION={exp_duration}',
            '-e', f'CLEAVE_CONTROL_HOST={host_addr}',
            '-e', f'CLEAVE_PLANT_INDEX={i}',
            '--volume', f'{output_dir}:/output:rw',
            cleave_docker_img,
            'cleave', '-vvvvv', f'--file-log=/output/plant_{i:02}',
            'run-plant', '/CLEAVE/experiment_setup/plant/config.py'
        ],
        env=env
    ) for i, addr in enumerate(addresses)]

    for p in procs:
        p.wait()


if __name__ == '__main__':
    main()