#  Copyright (c) 2020 KTH Royal Institute of Technology
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
import socket
import sys
from typing import Tuple

import click

from cleave.base.client import builder
from cleave.base.config import ConfigWrapper
from cleave.base.logging import loguru
from cleave.base.network.client import UDPControllerInterface

_plant_defaults = dict(
    controller_interface=UDPControllerInterface
)


@click.command()
@click.option('-a', '--host-address', type=(str, int), default=('', -1),
              show_default=False, required=False,
              help='IP address of the controller service, given as an '
                   '<hostname> <port> pair.')
@click.option('-v', '--verbose', count=True, default=0, show_default=False,
              help='Set the logging verbosity level.')
@click.option('-c/-nc', '--colorize-logs/--no-colorize-logs', type=bool,
              default=True, show_default=True, help='Colorize log output.')
@click.argument('config_file_path',
                # help='Path to the configuration script.',
                type=click.Path(exists=True,
                                file_okay=True,
                                dir_okay=False))
def run_plant(host_address: Tuple[str, int],
              verbose: int,
              colorize_logs: bool,
              config_file_path: str):
    host_addr_config = {} if host_address == ('', -1) \
        else {'host': host_address[0], 'port': host_address[1]}

    # configure logging
    log_level = loguru.logger.level('CRITICAL').no - (verbose * 10)
    loguru.logger.add(sys.stderr,
                      level=log_level,
                      colorize=colorize_logs,
                      format='<light-green>{time}</light-green> '
                             '<level><b>{level}</b></level> '
                             '{message}')

    config = ConfigWrapper(
        config_path=config_file_path,
        cmd_line_overrides=host_addr_config,
        defaults=_plant_defaults
    )

    host_addr = (socket.gethostbyname(config.host), config.port)
    builder.set_controller(config.controller_interface(host_addr))
    builder.set_plant_state(config.state)

    for sensor in config.sensors:
        builder.attach_sensor(sensor)

    for actuator in config.actuators:
        builder.attach_actuator(actuator)

    # TODO: extra options to build?
    plant = builder.build(plotting=True)
    plant.execute()


if __name__ == '__main__':
    run_plant()
