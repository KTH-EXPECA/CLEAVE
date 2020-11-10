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
from pathlib import Path
from typing import Tuple

import click

from cleave.core.client import builder
from cleave.core.config import ConfigWrapper
from cleave.core.eventloop import reactor
from cleave.core.logging import loguru
from cleave.core.network.backend import UDPControllerService
from cleave.core.network.client import UDPControllerInterface
from cleave.core.recordable import CSVRecorder

_control_defaults = dict(
    output_dir='./controller_metrics/',
    controller_service=UDPControllerService
)

_plant_defaults = dict(
    controller_interface=UDPControllerInterface,
    output_dir='./plant_metrics/',
    plant_sinks=[],
    client_sinks=[]
)


@click.group()
@click.option('-v', '--verbose', count=True, default=0, show_default=False,
              help='Set the logging verbosity level.')
@click.option('-c/-nc', '--colorize-logs/--no-colorize-logs', type=bool,
              default=True, show_default=True, help='Colorize log output.')
def cli(verbose: int, colorize_logs: bool):
    # configure logging
    log_level = max(loguru.logger.level('CRITICAL').no - (verbose * 10), 0)
    loguru.logger.add(sys.stderr,
                      level=log_level,
                      colorize=colorize_logs,
                      format='<light-green>{time}</light-green> '
                             '<level><b>{level}</b></level> '
                             '{message}')


@cli.command('run-plant')
@click.option('-a', '--host-address', type=(str, int), default=('', -1),
              show_default=False, required=False,
              help='IP address of the controller service, given as an '
                   '<hostname> <port> pair.')
@click.argument('config_file_path',
                type=click.Path(exists=True,
                                file_okay=True,
                                dir_okay=False))
def run_plant(host_address: Tuple[str, int],
              config_file_path: str):
    host_addr_config = {} if host_address == ('', -1) \
        else {'host': host_address[0], 'port': host_address[1]}

    config = ConfigWrapper(
        config_path=config_file_path,
        cmd_line_overrides=host_addr_config,
        defaults=_plant_defaults
    )

    host_addr = (socket.gethostbyname(config.host), config.port)
    builder.set_controller(config.controller_interface(host_addr))
    builder.set_plant_state(config.state)
    builder.set_sensors(config.sensors)
    builder.set_actuators(config.actuators)
    # builder.set_plant_sinks(config.plant_sinks)
    # builder.set_client_sinks(config.client_sinks)

    # TODO: extra options to build?
    plant = builder.build(csv_output_dir=config.output_dir)
    plant.execute()


@cli.command('run-controller')
@click.option('-p', '--bind-port', type=int, default=-1,
              show_default=False, required=False,
              help='Port to listen on for incoming control requests.')
@click.argument('config_file_path',
                type=click.Path(exists=True,
                                file_okay=True,
                                dir_okay=False))
def run_controller(bind_port: int,
                   config_file_path: str):
    port_override = {'port': bind_port} if bind_port > 0 else {}

    config = ConfigWrapper(
        config_path=config_file_path,
        cmd_line_overrides=port_override,
        defaults=_control_defaults
    )

    # TODO: modularize obtaining the reactor?
    service = config.controller_service(config.port, config.controller, reactor)

    # TODO: refactor this using composition
    # TODO: parameterize

    if config.output_dir:
        out_dir = Path(config.output_dir).resolve()

        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=False)
        elif not out_dir.is_dir():
            raise FileExistsError(f'{out_dir} exists and is not a '
                                  f'directory, aborting.')

        recorder = CSVRecorder(service, out_dir / 'service.csv')
        reactor.addSystemEventTrigger('before', 'startup', recorder.initialize)
        reactor.addSystemEventTrigger('after', 'shutdown', recorder.shutdown)

    service.serve()


if __name__ == '__main__':
    cli()

# TODO: check for """the kick"""
