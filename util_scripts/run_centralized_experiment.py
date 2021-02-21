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
import itertools
import os
import shutil
import subprocess
import time
import uuid
from multiprocessing import Pool
from pathlib import Path
from typing import Mapping, Optional

import click
import pytimeparse
import tqdm
from loguru import logger

logger.remove()

_compose_prefix = \
    '''
version: "3"
services:
    '''

_compose_service_template = \
    '''
  controller_{ctrl_index:02d}:
    image: {img_name}
    ports:
      - 500{ctrl_index:02d}:50000/udp
    volumes:
      - {output_dir}/controller_{ctrl_index:02d}:/output:rw
    entrypoint: "cleave -vvvvv run-controller \
                /CLEAVE/experiment_setup/controller/config.py"
    '''


def collect_results(base_output_dir: Path,
                    temp_output: Path,
                    plant_index: int,
                    plant_addr_template: str,
                    plant_output: str,
                    rpi_passwd: str,
                    rpi_user: str):
    logger.info(f'Collecting results for setup {plant_index:d}...')

    # set up target dir
    out_dir = base_output_dir / f'plant_{plant_index:02d}'
    out_dir.mkdir(parents=True, exist_ok=False)

    # origin dirs
    control_dir = temp_output / f'controller_{plant_index:02d}'
    plant_dir = f'{plant_output}/plant_{plant_index:02d}'

    # collect controller results
    for ctrl_file in control_dir.iterdir():
        shutil.copy(ctrl_file.resolve(), out_dir)

    # collect plant results
    subprocess.run(
        ['sshpass', '-p', rpi_passwd,
         'scp', '-oPubkeyAuthentication=no', '-oPasswordAuthentication=yes',
         '-r', f'{rpi_user}@{plant_addr_template.format(plant_index)}:'
               f'{plant_dir}', temp_output]
    )

    for plant_file in (temp_output / f'plant_{plant_index:02d}').iterdir():
        shutil.copy(plant_file.resolve(), out_dir)


def prepare_plant_docker_img(img_name: str,
                             plant_addr_template: str,
                             num_plants: int,
                             rpi_user: str,
                             rpi_passwd: str,
                             env: Optional[Mapping] = None):
    # make sure all plants have the necessary image
    procs = [subprocess.Popen(
        [
            'sshpass', '-p', rpi_passwd,
            'ssh', '-oPubkeyAuthentication=no', '-oPasswordAuthentication=yes',
            f'{rpi_user}@{plant_addr_template.format(i)}', '--',
            'docker', 'pull', img_name
        ],
        env=env
    ) for i in range(num_plants)]

    # wait for images to be pulled before continuing
    for p in procs:
        p.wait()


def prepare_controller_images(controller_temp_dir: Path,
                              num_plants: int,
                              img_name: str):
    out = _compose_prefix
    for i in range(num_plants):
        out += _compose_service_template.format(ctrl_index=i,
                                                img_name=img_name,
                                                output_dir=controller_temp_dir)

    with (controller_temp_dir / 'docker-compose.yml').open('w') as fp:
        print(out, file=fp)

    # pull clean new versions of images
    subprocess.run(
        ['docker-compose', 'rm', '-f'],
        cwd=controller_temp_dir
    )

    subprocess.run(
        ['docker-compose', 'pull'],
        cwd=controller_temp_dir
    )


@click.command()
@click.argument('host-addr', type=str)
@click.argument('num-plants', type=int)
@click.argument('output-dir',
                type=click.Path(exists=False, dir_okay=True, file_okay=False))
@click.option('-d', '--exp-duration',
              type=str, default='35m', show_default=True)
@click.option('--plant-addr-template',
              type=str, default='192.168.1.2{:02d}', show_default=True)
@click.option('--cleave_docker_img',
              type=str, default='molguin/cleave:cleave', show_default=True)
@click.option('-u', '--rpi-user',
              type=str, default='pi', show_default=True)
@click.option('-p', '--rpi-passwd',
              type=str, default='raspberry', show_default=True)
@click.option('-c', '--controller-temp-dir',
              default=f'/tmp/{uuid.uuid4()}',
              show_default=False,
              type=click.Path(exists=False))
@click.option('-l', '--plant-temp-dir',
              type=str, show_default=True,
              default='/home/pi/cleave')
@click.option('-n', '--nprocs', type=int, default=6, show_default=True)
@click.option('-v', '--verbose', count=True, default=0, show_default=False,
              help='Set the STDERR logging verbosity level.')
def main(host_addr: str,
         num_plants: int,
         output_dir: str,
         exp_duration: str = '35m',
         plant_addr_template: str = '192.168.1.2{:02d}',
         cleave_docker_img: str = 'molguin/cleave:cleave',
         rpi_user: str = 'pi',
         rpi_passwd: str = 'raspberry',
         controller_temp_dir: str = f'/tmp/{uuid.uuid4()}',
         plant_temp_dir: str = '/home/pi/cleave',
         nprocs: int = 6,
         verbose: int = 0):
    # Set log level
    log_level = max(logger.level('CRITICAL').no - (verbose * 10), 0)
    logger.add(lambda msg: tqdm.tqdm.write(msg, end=""),
               enqueue=True,
               level=log_level,
               colorize=True,
               format='<light-green>{time}</light-green> '
                      '<level><b>{level}</b></level> '
                      '{message}')

    # first things first, make sure the output dir exists and is empty
    base_output_dir = Path(output_dir).resolve()
    base_output_dir.mkdir(parents=True, exist_ok=False)

    env = dict(os.environ)
    env['DEBIAN_FRONTEND'] = 'noninteractive'

    prepare_plant_docker_img(cleave_docker_img,
                             plant_addr_template,
                             num_plants,
                             rpi_user,
                             rpi_passwd,
                             env=env)
    logger.info('Plant images pulled and ready.')

    # make the controller temp dir
    controller_temp_dir = Path(controller_temp_dir).resolve()
    controller_temp_dir.mkdir(parents=True, exist_ok=False)
    prepare_controller_images(controller_temp_dir,
                              num_plants,
                              cleave_docker_img)
    logger.info('Controller images pulled and ready.')

    # start
    for t in range(5, 0, -1):
        logger.warning(f'Starting experiment in {t}...')
        time.sleep(1.0)

    # spawn controller using temporary docker-compose.yml
    subprocess.run(['docker-compose', 'up', '-d'], cwd=controller_temp_dir)
    logger.info(f'Spawned {num_plants} controllers.')

    # spawn plants
    # each plant connects to a different port on the host
    procs = [subprocess.Popen(
        [
            'sshpass', '-p', rpi_passwd,
            'ssh', '-oPubkeyAuthentication=no', '-oPasswordAuthentication=yes',
            f'{rpi_user}@{plant_addr_template.format(i)}', '--',
            'docker', 'run', '--rm', '-d',
            '-e', f'OUTPUT_DIR=/output/plant_{i:02}',
            '-e', f'CLEAVE_DURATION={exp_duration}',
            '-e', f'CLEAVE_CONTROL_HOST={host_addr}',
            '-e', f'CLEAVE_PLANT_INDEX={i}',
            '--volume', f'{plant_temp_dir}:/output:rw',
            cleave_docker_img,
            'cleave', '-vvvvv', f'--file-log=/output/plant_{i:02}/plant.log',
            'run-plant', '/CLEAVE/experiment_setup/plant/config.py'
        ],
        env=env
    ) for i in range(num_plants)]

    for p in procs:
        p.wait()

    duration = pytimeparse.parse(exp_duration)
    delta_t = duration / 100

    logger.info('Running experiment, please wait...')
    for _ in tqdm.trange(100, desc='Progress...', leave=False):
        time.sleep(delta_t)

    logger.warning('Experiment finishing...')
    logger.warning('Adding 20s of buffer time just in case.')
    for _ in tqdm.trange(20, desc='Finishing experiment...', leave=False):
        time.sleep(1.0)

    logger.warning('Shutting down controller instances.')
    subprocess.run(['docker-compose', 'kill', '-s', 'SIGINT'],
                   cwd=controller_temp_dir)

    # collect results per plant, in parallel
    with Pool(nprocs) as pool:
        pool.starmap(collect_results,
                     zip(
                         itertools.repeat(base_output_dir),
                         itertools.repeat(controller_temp_dir),
                         range(num_plants),
                         itertools.repeat(plant_addr_template),
                         itertools.repeat(plant_temp_dir),
                         itertools.repeat(rpi_passwd),
                         itertools.repeat(rpi_user),
                     ))


if __name__ == '__main__':
    main()
