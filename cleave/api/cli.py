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
from typing import Optional

import click
from twisted.internet import reactor
from twisted.internet.error import ReactorNotRunning
from twisted.internet.posixbase import PosixReactorBase

from cleave.core.client.control import BaseControllerInterface
from cleave.core.client.physicalsim import PhysicalSimulation
from cleave.core.client.plant import CSVRecordingPlant
from cleave.core.config import Config, ConfigFile
from cleave.core.logging import loguru
from cleave.core.network.backend import BaseControllerService, \
    UDPControllerService
from cleave.core.network.client import RecordingUDPControlClient

reactor: PosixReactorBase = reactor

_control_defaults = dict(
    output_dir='./controller_metrics/',
    controller_service=UDPControllerService,
    startup_callbacks=[],
    shutdown_callbacks=[],
    # TODO: remove
)

_plant_defaults = dict(
    output_dir='./plant_metrics/',
    controller_params={},
    startup_callbacks=[],
    shutdown_callbacks=[],
)


def shutdown(reactor: PosixReactorBase):
    try:
        reactor.stop()
    except ReactorNotRunning:
        pass


def setup_plant(config: Config, reactor: PosixReactorBase):
    output_dir = Path(config.output_dir)

    class UDPClient(RecordingUDPControlClient):
        def on_start(self, control_i: BaseControllerInterface):
            plant = CSVRecordingPlant(
                physim=PhysicalSimulation(
                    state=config.state,
                    tick_rate=config.tick_rate
                ),
                sensors=config.sensors,
                actuators=config.actuators,
                control_interface=control_i,
                recording_output_dir=output_dir
            )
            d = plant.set_up(reactor=reactor, duration=config.emu_duration)
            d.addBoth(lambda _: self.transport.stopListening())

        def on_end(self):
            shutdown(reactor)

    host = socket.gethostbyname(config.host)
    proto = UDPClient((host, config.port),
                      output_dir=output_dir)
    proto.register_with_reactor(reactor)


@click.group()
# @click.pass_context
@click.option('-i', '--version', is_flag=True,
              help='Print the framework version and exit')
@click.option('-v', '--verbose', count=True, default=0, show_default=False,
              help='Set the STDERR logging verbosity level.')
@click.option('-c/-nc', '--colorize-logs/--no-colorize-logs', type=bool,
              default=True, show_default=True, help='Colorize log output.')
@click.option('-f', '--file-log', type=click.Path(file_okay=True,
                                                  dir_okay=False),
              help='Save log to the specified file. File logs are always set '
                   'to maximum verbosity.')
def cli(version: bool,
        verbose: int,
        colorize_logs: bool,
        file_log: Optional[str] = None):
    """
    Launch a CLEAVE emulation. For details on each subcommand, please run

    cleave SUBCOMMAND --help
    """

    if version:
        from .. import __version__
        print(__version__)
        exit(0)

    # if ctx.invoked_subcommand is None:
    #     click.echo(ctx.get_help())

    # configure logging
    log_level = max(loguru.logger.level('CRITICAL').no - (verbose * 10), 0)
    loguru.logger.add(sys.stderr,
                      level=log_level,
                      colorize=colorize_logs,
                      format='<light-green>{time}</light-green> '
                             '<level><b>{level}</b></level> '
                             '{message}')

    if file_log is not None:
        loguru.logger.add(file_log,
                          level=loguru.logger.level('DEBUG').no,
                          colorize=False,
                          format='<light-green>{time}</light-green> '
                                 '<level><b>{level}</b></level> '
                                 '{message}')


@cli.command('run-plant')
@click.argument('config_file_path',
                type=click.Path(exists=True,
                                file_okay=True,
                                dir_okay=False))
def run_plant(config_file_path: str):
    """
    Execute a CLEAVE Plant.
    """
    config = ConfigFile(
        config_path=config_file_path,
        defaults=_plant_defaults
    )

    # build a controller interface

    setup_plant(config, reactor)

    reactor.suggestThreadPoolSize(3)
    for c in config.startup_callbacks:
        reactor.addSystemEventTrigger('during', 'startup', c)
    for c in config.shutdown_callbacks:
        reactor.addSystemEventTrigger('during', 'shutdown', c)
    reactor.run()


@cli.command('run-controller')
@click.argument('config_file_path',
                type=click.Path(exists=True,
                                file_okay=True,
                                dir_okay=False))
def run_controller(config_file_path: str):
    """
    Execute a CLEAVE Controller Service.
    """

    config = ConfigFile(
        config_path=config_file_path,
        defaults=_control_defaults
    )

    service: BaseControllerService = config.controller_service(
        config.controller,
        Path(config.output_dir))
    for c in config.startup_callbacks:
        reactor.addSystemEventTrigger('during', 'startup', c)
    for c in config.shutdown_callbacks:
        reactor.addSystemEventTrigger('during', 'shutdown', c)

    reactor.getThreadPool().adjustPoolsize(minthreads=3,
                                           maxthreads=10)
    reactor.listenUDP(config.port, service.protocol)
    reactor.run()
