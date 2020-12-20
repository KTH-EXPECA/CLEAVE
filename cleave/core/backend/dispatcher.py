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
import json
import multiprocessing as mp
import os
import signal
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple, Type

from klein import Klein
from klein.resource import KleinResource
from twisted.internet import endpoints
from twisted.internet.posixbase import PosixReactorBase
from twisted.web import server
from twisted.web.http import Request
from twisted.web.server import Site

from . import schemas
from .web_utils import MalformedRequest, json_decode_errback, \
    json_endpoint, malformed_request, write_json_response
from ..logging import Logger
from ..network.backend import UDPControllerService
from ...api.controller import Controller


class ControllerProcessResource:
    def __init__(self,
                 control_cls: Type[Controller],
                 params: Mapping[str, Any]):
        super(ControllerProcessResource, self).__init__()
        self._id = uuid.uuid4()
        self._app = Klein()
        self._app.route('/status', methods=['GET'])(self.info)
        self._controller_cls = control_cls
        self._params = params

        out_q = mp.Queue()
        self._process = mp.Process(
            target=ControllerProcessResource._control_process,
            args=(control_cls, params, str(self._id), out_q))
        self._process.start()
        self._interface, self._port, self._out_path = out_q.get()

    @property
    def controller_class(self) -> Type[Controller]:
        return self._controller_cls

    @property
    def controller_params(self) -> Mapping[str, Any]:
        return self._params

    @property
    def port(self) -> int:
        return self._port

    @property
    def address(self) -> str:
        return self._interface

    @property
    def out_path(self) -> Path:
        return self._out_path

    @property
    def resource(self) -> KleinResource:
        return self._app.resource()

    @property
    def uuid(self) -> uuid.UUID:
        return self._id

    def info(self, req: Request) -> Any:
        # ensure_headers(req, {'content-type': 'application/json'})
        write_json_response(
            request=req,
            response={
                'id'        : f'{self._id}',
                'process_id': self._process.pid,
                'interface' : self._interface,
                'port'      : self._port
            },
            status_code=200
        )
        return server.NOT_DONE_YET

    def shut_down(self, timeout: float = 5) -> None:
        os.kill(self._process.pid, signal.SIGINT)
        try:
            self._process.join(timeout=timeout)
        except TimeoutError:
            self._process.terminate()
            self._process.join()

    @staticmethod
    def _control_process(control_cls: Type[Controller],
                         params: Mapping[str, Any],
                         uid: str,
                         out_q: mp.Queue) -> None:
        from twisted.internet import reactor
        reactor: PosixReactorBase = reactor

        controller = control_cls(**params)
        path = Path(f'./controllers/{uid}').resolve()
        service = UDPControllerService(
            controller=controller,
            output_dir=path)

        port = reactor.listenUDP(0, service.protocol)
        out_q.put((port.interface, port.port, path))
        reactor.run()


class Dispatcher:
    def __init__(self, controllers: Mapping[str, Type[Controller]]):
        super(Dispatcher, self).__init__()
        self._log = Logger()
        self._app = Klein()
        self._ctrl_res: Dict[uuid.UUID, ControllerProcessResource] = dict()
        self._controller_cls = controllers

        # set up routes
        # TODO: for some reason, this defaults to DELETE?
        self._app.route('/', methods=['GET'])(self.list_controllers)
        self._app.route('/', methods=['POST'])(self.spawn_controller)
        self._app.route('/', methods=['DELETE'])(self.shutdown_controller)

        # route for spawned controllers
        self._app.route('/<string:ctrl_id>', branch=True) \
            (self.controller_resource)

        self._app.handle_errors(MalformedRequest)(malformed_request)
        self._app.handle_errors(json.JSONDecodeError)(json_decode_errback)

    def run(self, host: str, port: int) -> None:
        from twisted.internet import reactor
        reactor: PosixReactorBase = reactor

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
        reactor.run()

    @json_endpoint(schemas.spawn_controller)
    def spawn_controller(self, req_dict: Mapping[str, Any]) \
            -> Tuple[int, Mapping]:

        controller_cls = req_dict['controller']
        parameters = req_dict['params']

        ctrl_resource = ControllerProcessResource(
            control_cls=controller_cls,
            params=parameters
        )
        self._ctrl_res[ctrl_resource.uuid] = ctrl_resource

        resp_dict = {
            'controller': str(ctrl_resource.uuid),
            'host'      : ctrl_resource.address,
            'port'      : ctrl_resource.port,
            'log_path'  : ctrl_resource.out_path
        }
        return 200, resp_dict

    @json_endpoint(schemas.shutdown_controller)
    def shutdown_controller(self, req_dict: Mapping[str, Any]) -> Any:
        try:
            controller_uuid = uuid.UUID(req_dict['id'])
            res = self._ctrl_res[controller_uuid]
        except ValueError:
            return 400, {'error', 'Could not parse controller UUID.'}
        except KeyError:
            return 404, {'error', f'No such controller {req_dict["id"]}.'}

        res.shut_down()
        return 200

    def list_controllers(self, request: Request) -> Any:

        controllers = [
            {
                'id'        : str(c_id),
                'controller':
                    ctrl.controller_class.__name__,
                'parameters': ctrl.controller_params,
            }
            for c_id, ctrl in self._ctrl_res.items()
        ]

        write_json_response(request=request,
                            response={'controllers': controllers},
                            status_code=200)
        return server.NOT_DONE_YET

    def controller_resource(self,
                            request: Request,
                            ctrl_id: str) -> Any:
        try:
            ctrl_id = uuid.UUID(ctrl_id)
            return self._ctrl_res[ctrl_id].resource
        except ValueError:
            write_json_response(
                request=request,
                response={'error': f'Malformed uuid {ctrl_id}'},
                status_code=400
            )
        except KeyError:
            write_json_response(
                request=request,
                response={'error': f'No such controller: {ctrl_id}'},
                status_code=404
            )
        return server.NOT_DONE_YET
