#!/usr/bin/env python

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

import click
from twisted.internet.posixbase import PosixReactorBase

from cleave.core.backend.dispatcher import Dispatcher
from cleave.core.client.physicalsim import PhysicalSimulation
from cleave.core.client.plant import CSVRecordingPlant, Plant
from cleave.core.config import Config, ConfigFile
from cleave.core.logging import loguru
from cleave.core.network.backend import BaseControllerService, \
    UDPControllerService
from cleave.core.network.client import UDPControllerInterface

_control_defaults = dict(
    output_dir='./controller_metrics/',
    controller_service=UDPControllerService
)

_plant_defaults = dict(
    controller_interface=UDPControllerInterface,
    output_dir='./plant_metrics/',
)


def build_plant_from_config(config: Config) -> Plant:
    """
    Builds a Plant from a given configuration.

    Parameters
    ----------
    config
        Config containing the necessary parameters for the Plant.

    Returns
    -------
        A fully assembled Plant.

    """
    host_addr = (socket.gethostbyname(config.host), config.port)
    return CSVRecordingPlant(
        physim=PhysicalSimulation(
            state=config.state,
            tick_rate=config.tick_rate
        ),
        sensors=config.sensors,
        actuators=config.actuators,
        control_interface=config.controller_interface(host_addr),
        recording_output_dir=Path(config.output_dir)
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
@click.argument('config_file_path',
                type=click.Path(exists=True,
                                file_okay=True,
                                dir_okay=False))
def run_plant(config_file_path: str):
    config = ConfigFile(
        config_path=config_file_path,
        defaults=_plant_defaults
    )

    plant = build_plant_from_config(config)
    plant.execute()


@cli.command('run-controller')
@click.argument('config_file_path',
                type=click.Path(exists=True,
                                file_okay=True,
                                dir_okay=False))
def run_controller(config_file_path: str):
    from twisted.internet import reactor
    reactor: PosixReactorBase = reactor

    config = ConfigFile(
        config_path=config_file_path,
        defaults=_control_defaults
    )

    service: BaseControllerService = config.controller_service(
        config.controller,
        Path(config.output_dir))
    reactor.listenUDP(config.port, service.protocol)
    reactor.run()


@cli.command('run-dispatcher')
@click.argument('port', type=int)
def run_dispatcher(port: int):
    from twisted.internet import reactor
    from cleave.impl.inverted_pendulum import InvPendulumController
    reactor: PosixReactorBase = reactor

    # TODO: parameterize
    dispatcher = Dispatcher({'InvPendulumController': InvPendulumController})
    dispatcher.run('localhost', 8080)


if __name__ == '__main__':
    cli()
