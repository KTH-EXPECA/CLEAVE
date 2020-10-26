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
import sys

import click

from cleave.base.config import ConfigWrapper
from cleave.base.eventloop import reactor
from cleave.base.logging import loguru
from cleave.base.network.backend import UDPControllerService

_control_defaults = dict(
    controller_service=UDPControllerService
)


@click.command()
@click.option('-p', '--bind-port', type=int, default=-1,
              show_default=False, required=False,
              help='Port to listen on for incoming control requests.')
@click.option('-v', '--verbose', count=True, default=0, show_default=False,
              help='Set the logging verbosity level.')
@click.option('-c/-nc', '--colorize-logs/--no-colorize-logs', type=bool,
              default=True, show_default=True, help='Colorize log output.')
@click.argument('config_file_path',
                # help='Path to the configuration script.',
                type=click.Path(exists=True,
                                file_okay=True,
                                dir_okay=False))
def run_controller(bind_port: int,
                   verbose: int,
                   colorize_logs: bool,
                   config_file_path: str):
    port_override = {'port': bind_port} if bind_port > 0 else {}

    # configure logging
    log_level = max(loguru.logger.level('CRITICAL').no - (verbose * 10), 0)
    loguru.logger.add(sys.stderr,
                      level=log_level,
                      colorize=colorize_logs,
                      format='<light-green>{time}</light-green> '
                             '<level><b>{level}</b></level> '
                             '{message}')

    config = ConfigWrapper(
        config_path=config_file_path,
        cmd_line_overrides=port_override,
        defaults=_control_defaults
    )

    # TODO: modularize obtaining the reactor?
    service = config.controller_service(config.port, config.controller, reactor)
    service.serve()


if __name__ == '__main__':
    run_controller()
