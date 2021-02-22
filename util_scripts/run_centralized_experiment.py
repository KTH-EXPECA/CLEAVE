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
              help='Duration of this experiment. Should be specified in a '
                   '<duration><unit> manner; e.g. 35m for 35 minutes, '
                   '1h20m for an hour and 20 minutes, 10s for 10 seconds, '
                   'and so on.',
              type=str, default='10s', show_default=True)
@click.option('--plant-addr-template',
              help='Template string used to format Plant IP addresses based '
                   'on the Plant index. Will be formatted by calling '
                   '<format_string>.format(plant_index).',
              type=str, default='192.168.1.2{:02d}', show_default=True)
@click.option('--cleave_docker_img',
              help='Docker image used for the experiment. Should be available '
                   'for linux/amd64 and linux/armv7 platforms, as the same '
                   'image will be used for both the Controllers and the '
                   'Plants.',
              type=str, default='molguin/cleave:cleave', show_default=True)
@click.option('-u', '--rpi-user',
              help='User used to log in and deploy the Plants on the '
                   'Raspberry Pis.',
              type=str, default='pi', show_default=True)
@click.option('-p', '--rpi-passwd',
              help='Password for the user used to log in and deploy the '
                   'Plants on the Raspberry Pis.',
              type=str, default='raspberry', show_default=True)
@click.option('-c', '--controller-temp-dir',
              help='Local temporary directory where the output of the '
                   'Controllers will be stored before collection. By default '
                   'this corresponds to /tmp/<experiment_id>',
              default=None,
              show_default=False,
              type=click.Path(exists=False))
@click.option('-l', '--plant-temp-dir',
              type=str, show_default=True,
              help='Remote temporary directory where the output of the '
                   'Plants will be stored on each Raspberry Pi before '
                   'collection. By default this corresponds to '
                   '/home/<user>/cleave/<experiment_id>',
              default=None)
@click.option('-n', '--nprocs',
              help='Number of parallel processes to use for final data '
                   'collection.',
              type=int, default=6, show_default=True)
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
         controller_temp_dir: Optional[str] = None,
         plant_temp_dir: Optional[str] = None,
         nprocs: int = 6,
         verbose: int = logger.level('INFO').no):
    """
    Run an experiment setup.

    What this script does:

        1. Sets up the appropriate number of containerized Docker instances
        locally.

        2. Sets up a matching number of remote Plant containers on
        Raspberry Pi devices on the network.

        3. Executes the experiment and waits for it to finish.

        4. Once the experiment finishes, it collects the local and remote
        data into a specified folder.
    """

    # Set log level
    log_level = max(logger.level('CRITICAL').no - (verbose * 10), 0)
    logger.add(lambda msg: tqdm.tqdm.write(msg, end=""),
               enqueue=True,
               level=log_level,
               colorize=True,
               format='<light-green>{time}</light-green> '
                      '<level><b>{level}</b></level> '
                      '{message}')

    experiment_id = uuid.uuid4()

    # make sure the duration can be parsed
    duration = pytimeparse.parse(exp_duration)

    logger.info(f'Initializing experiment run with ID {experiment_id}.')
    logger.info(f'Target duration: {exp_duration} ({duration} seconds).')

    if controller_temp_dir is None:
        controller_temp_dir = f'/tmp/{experiment_id}'
    if plant_temp_dir is None:
        plant_temp_dir = f'/home/{rpi_user}/cleave/{experiment_id}'

    # first things first, make sure the output dir exists and is empty
    base_output_dir = Path(output_dir).resolve()
    base_output_dir.mkdir(parents=True, exist_ok=False)

    logger.info(f'Results will be output to {base_output_dir}.')

    # make the controller temp dir
    controller_temp_dir = Path(controller_temp_dir).resolve()
    controller_temp_dir.mkdir(parents=True, exist_ok=False)

    logger.info(f'Controller temporary data will be output to '
                f' {controller_temp_dir}')
    logger.info(f'Plant temporary data will be output to {plant_temp_dir}')

    env = dict(os.environ)
    env['DEBIAN_FRONTEND'] = 'noninteractive'

    prepare_plant_docker_img(cleave_docker_img,
                             plant_addr_template,
                             num_plants,
                             rpi_user,
                             rpi_passwd,
                             env=env)
    logger.info('Plant images pulled and ready.')

    prepare_controller_images(controller_temp_dir,
                              num_plants,
                              cleave_docker_img)
    logger.info('Controller images pulled and ready.')

    logger.warning('EXPERIMENT CANNOT BE CANCELLED AFTER STARTED.')
    logger.warning('Once experiment starts, you will have to wait until it is '
                   'finished to change any configuration.')
    logger.warning('Press Ctrl-C to abort now or wait for experiment to begin.')

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

    delta_t = duration / 100

    logger.info('Running experiment, please wait...')
    for _ in tqdm.trange(100, desc='Progress...', leave=False):
        time.sleep(delta_t)

    logger.warning('Experiment finishing...')
    logger.info('Adding 20s of buffer time just in case.')
    for _ in tqdm.trange(20, desc='Finishing experiment...', leave=False):
        time.sleep(1.0)

    logger.info('Shutting down controller instances.')
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

    logger.info(f'Finished experiment {experiment_id}.')
    logger.info(f'Controller temporary data remains at'
                f' {controller_temp_dir}')
    logger.info(f'Plant temporary data remains at {plant_temp_dir}')
    logger.info(f'Final results were collected to {output_dir}')


if __name__ == '__main__':
    main()
