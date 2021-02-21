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
import itertools
import shutil
import subprocess
from multiprocessing import Pool
from pathlib import Path

import click


def _collect_results(base_output_dir: Path,
                     ctrl_output: Path,
                     plant_index: int,
                     num_plants: int,
                     plant_addr_template: str,
                     plant_output: str,
                     rpi_passwd: str,
                     rpi_user: str):
    print(f'Collecting results for setup {plant_index:d} out of {num_plants:d}')

    # set up target dir
    out_dir = base_output_dir / f'plant_{plant_index:02d}'
    out_dir.mkdir(parents=True, exist_ok=False)

    # collect controller results
    for ctrl_file in (ctrl_output / f'controller_{plant_index:02d}').iterdir():
        shutil.copy(ctrl_file.resolve(), out_dir)

    # collect plant results
    subprocess.run(
        ['sshpass', '-p', rpi_passwd,
         'scp', '-oPubkeyAuthentication=no', '-oPasswordAuthentication=yes',
         f'{rpi_user}@{plant_addr_template.format(plant_index)}:'
         f'"{plant_output}/plant_{plant_index:02d}/*"', out_dir]
    )


@click.command()
@click.argument('controller-output', type=str)
@click.argument('num-plants', type=int)
@click.argument('plant-output', type=str)
@click.argument('target-dir', type=str)
@click.option('-a', '--plant-address-template', type=str,
              default='192.168.1.2{:02d}', show_default=True)
@click.option('-u', '--rpi-user', type=str,
              default='pi', show_default=True)
@click.option('-p', '--rpi-passwd', type=str,
              default='raspberry', show_default=True)
@click.option('-n', '--nprocs', type=int,
              default=6, show_default=True)
def main(controller_output: str,
         num_plants: int,
         plant_output: str,
         target_dir: str,
         plant_addr_template: str = '192.168.1.2{:02d}',
         rpi_user: str = 'pi',
         rpi_passwd: str = 'raspberry',
         nprocs: int = 6):
    # collect results per plant, in parallel
    ctrl_output = Path(controller_output).resolve()
    base_output_dir = Path(target_dir).resolve()

    with Pool(nprocs) as pool:
        pool.starmap(_collect_results,
                     zip(
                         itertools.repeat(base_output_dir),
                         itertools.repeat(ctrl_output),
                         range(num_plants),
                         itertools.repeat(num_plants),
                         itertools.repeat(plant_addr_template),
                         itertools.repeat(plant_output),
                         itertools.repeat(rpi_passwd),
                         itertools.repeat(rpi_user)
                     ))
    print('Done')


if __name__ == '__main__':
    main()
