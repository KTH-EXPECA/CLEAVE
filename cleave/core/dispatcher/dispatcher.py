#  Copyright (c) 2020 KTH Royal Institute of Technology
#
#  Licensed under the Apache License, Version 2.0 (the 'License');
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an 'AS IS' BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import inspect
import json
import os
import uuid
from typing import Any, Mapping, Tuple, Type

from klein import Klein
from twisted.internet import endpoints, reactor
from twisted.internet.error import ProcessDone
from twisted.internet.posixbase import PosixReactorBase
from twisted.internet.protocol import ProcessProtocol
from twisted.python.failure import Failure
from twisted.web import server
from twisted.web.http import Request
from twisted.web.server import Site

from . import standalone_controller
from .web_utils import json_endpoint, spawn_controller_schema, \
    write_json_response
from ..logging import Logger
from ...api.controller import Controller

reactor: PosixReactorBase = reactor


class Dispatcher:
    """
    Implementation of an HTTP server for dynamic spawning of controller.
    """

    def __init__(self, controllers: Mapping[str, Type[Controller]]):
        """

        Parameters
        ----------
        controllers
            Mapping from string to Controller class.
        """
        super(Dispatcher, self).__init__()
        self._log = Logger()
        self._app = Klein()
        self._running_controllers = dict()
        self._warming_up_controllers = set()
        self._controller_classes = controllers

        # set up routes
        self._app.route('/', methods=['GET', 'POST']) \
            (lambda request: {
                'GET' : self.list_controllers,
                'POST': self.spawn_controller,
            }[request.method.decode('utf8')](request))

        # routes for spawned controllers
        self._app.route('/<string:ctrl_id>', methods=['GET', 'DELETE']) \
            (lambda request: {
                'GET'   : self.controller_info,
                'DELETE': self.shutdown_controller,
            }[request.method.decode('utf8')](request))

    def set_up(self, host: str, port: int) -> None:
        """
        Initializes the server, listening on host:port.

        Parameters
        ----------
        host
            Interface on which to listen.
        port
            Port on which to accept incoming requests.
        """

        # Create desired endpoint
        host = host.replace(':', '\:')
        endpoint_description = f'tcp:port={port}:interface={host}'
        endpoint = endpoints.serverFromString(reactor, endpoint_description)

        def listen_callback(port):
            addr = port.getHost()
            self._log.info(f'Dispatcher HTTP server listening on '
                           f'http://{addr.host}:{addr.port}')

        # This actually starts listening on the endpoint with the Klein app
        d = endpoint.listen(Site(self._app.resource()))
        d.addCallback(listen_callback)

    @json_endpoint(spawn_controller_schema)
    def spawn_controller(self,
                         req_dict: Mapping[str, Any]) -> Tuple[int, Mapping]:
        """
        Dynamically spawns a Controller Service.
        """
        controller_cls = req_dict['controller']

        # get actual controller class and its module
        try:
            controller = self._controller_classes[controller_cls]
            module = inspect.getmodule(controller)
            if module is None:
                return 400, {'error': f'Could not find a module associated '
                                      f'with controller {controller_cls}.'}
        except KeyError:
            return 400, {'error': f'No such controller class {controller_cls}.'}

        parameters = req_dict.get('params', {})
        controller_id = uuid.uuid4()

        args = json.dumps(dict(
            id=str(controller_id),
            controller=controller.__name__,
            module=module.__name__,
            params=parameters,
        ), separators=(',', ':'), indent=None)

        # create an internal ProcessProtocol to bind some callbacks
        class CtrlProcProtocol(ProcessProtocol):
            # keep a reference to the dispatcher
            dispatcher = self

            def outReceived(self, data: bytes):
                # once we receive the info, the controller process is ready
                # now we can update the dispatcher with the info
                info = json.loads(data.decode('utf8'))
                host = info['host']
                port = info['port']

                self.dispatcher._warming_up_controllers.remove(controller_id)
                self.dispatcher._running_controllers[controller_id] = \
                    {
                        'protocol': self,
                        'info'    : info
                    }

                self.transport.closeStdout()
                self.dispatcher._log.info(
                    f'Controller {controller_id} is ready and listening on '
                    f'{port}:{host}.')

            def errReceived(self, data: bytes):
                msg = data.decode('utf8')
                self.dispatcher._log.error(f'Controller {controller_id}: ',
                                           msg)

            def shutdown(self) -> None:
                self.dispatcher._log.warn(f'Controller {controller_id} '
                                          f'shutting down.')
                self.transport.signalProcess('INT')

            def processEnded(self, fail: Failure):
                if not (isinstance(fail.value, ProcessDone)
                        or fail.value.exitCode == 0):
                    self._log.error(
                        f'Controller {self._id} exited with exit code '
                        f'{fail.value.exitCode}!'
                    )

                # remove the controller from the dispatcher
                self.dispatcher._running_controllers.pop(controller_id)
                self._log.warn(f'Controller {self._id} shut down.')

        self._warming_up_controllers.add(controller_id)
        reactor.spawnProcess(
            CtrlProcProtocol(),
            executable='python',
            args=(
                'python',
                standalone_controller.__file__,
                args,
            ),
            env=None,
            path=os.getcwd()
        )
        return 202, {'id': str(controller_id)}

    def list_controllers(self, request: Request) -> Any:
        controllers = {
            str(c_id): ctrl_dict['info']
            for c_id, ctrl_dict in self._running_controllers.items()
        }

        write_json_response(request=request,
                            response=controllers,
                            status_code=200)
        return server.NOT_DONE_YET

    def shutdown_controller(self,
                            request: Request,
                            ctrl_id: str) -> Any:
        try:
            controller_uuid = uuid.UUID(ctrl_id)
            controller_dict = self._running_controllers[controller_uuid]
            controller_dict['protocol'].shutdown()
            request.setResponseCode(202)
            request.finish()
        except ValueError:
            write_json_response(
                request=request,
                response={'error': 'Could not parse controller UUID.'},
                status_code=400,
            )
        except KeyError:
            write_json_response(
                request=request,
                response={'error': f'No such controller {ctrl_id}.'},
                status_code=404
            )
        return server.NOT_DONE_YET

    def controller_info(self,
                        request: Request,
                        ctrl_id: str) -> Any:
        try:
            ctrl_id = uuid.UUID(ctrl_id)
            controller_dict = self._running_controllers[ctrl_id]

            write_json_response(
                request=request,
                response=controller_dict['info'],
                status_code=200
            )
        except ValueError:
            write_json_response(
                request=request,
                response={'error': f'Malformed uuid {ctrl_id}'},
                status_code=400
            )
        except KeyError:
            if ctrl_id in self._warming_up_controllers:
                write_json_response(
                    request=request,
                    response={'status': 'Not ready.'},
                    status_code=202
                )
            else:
                write_json_response(
                    request=request,
                    response={'error': f'No such controller: {ctrl_id}'},
                    status_code=404
                )
        return server.NOT_DONE_YET
