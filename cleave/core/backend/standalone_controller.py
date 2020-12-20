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
import importlib
import json
from pathlib import Path
from typing import Any, Mapping

import click
import loguru
from twisted.internet.posixbase import PosixReactorBase

from cleave.core.network.backend import UDPControllerService


class JSON(click.ParamType):
    name = 'JSON'

    def convert(self, value, param, ctx):
        try:
            config = json.loads(value)
            return config
        except json.JSONDecodeError:
            self.fail(
                f'failed to decode param "{value}" as a JSON object.',
                param,
                ctx
            )


@click.command()
@click.argument('config',
                type=JSON())
def run_controller(config: Mapping[str, Any]) -> None:
    """
    Runs a standalone controller.
    """

    from twisted.internet import reactor
    reactor: PosixReactorBase = reactor

    ctrl_mod = importlib.import_module(config['module'])
    ctrl_class = getattr(ctrl_mod, config['controller'])
    params = config['params']
    uuid = config['id']

    controller = ctrl_class(**params)
    path = Path(f'/tmp/controllers/{uuid}').resolve()
    service = UDPControllerService(
        controller=controller,
        output_dir=path)

    loguru.logger.add(path / 'controller.log',
                      level=10,
                      colorize=False,
                      format='<light-green>{time}</light-green> '
                             '<level><b>{level}</b></level> '
                             '{message}')

    port = reactor.listenUDP(0, service.protocol).getHost()
    # out_q.put((port.interface, port.port, path))
    reactor.callWhenRunning(
        lambda: print(json.dumps({
            'controller': config['controller'],
            'path'      : str(path),
            'params'    : params,
            'host'      : port.host,
            'port'      : port.port
        }, indent=None, separators=(',', ':')))
    )
    reactor.run()


if __name__ == '__main__':
    run_controller()
