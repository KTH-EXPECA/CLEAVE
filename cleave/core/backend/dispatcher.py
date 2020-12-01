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
import json
import uuid
from typing import Any, Mapping

from klein import Klein
from klein.resource import KleinResource
from twisted.internet import endpoints
from twisted.internet.posixbase import PosixReactorBase
from twisted.python.failure import Failure
from twisted.web import server
from twisted.web.http import Request
from twisted.web.server import Site


class MalformedRequest(Exception):
    pass


def _write_json_response(request: Request,
                         status_code: int,
                         response: Mapping,
                         finish: bool = True) -> None:
    request.setResponseCode(status_code)
    request.setHeader('content-type', 'application/json')
    request.write(json.dumps(response).encode('utf8'))
    if finish:
        request.finish()


def ensure_headers(req: Request, headers: Mapping[str, str]) -> None:
    for header, exp_value in headers.items():
        req_value = req.getHeader(header)
        if req_value is None or req_value.lower() != exp_value.lower():
            raise MalformedRequest()


class ControllerResource:
    def __init__(self):
        # TODO: wrap actual controller

        self._id = uuid.uuid4()
        self._app = Klein()
        # relative routes
        self._app.route('/controller', methods=['GET'])(self.info)
        self._app.route('/controller', methods=['DELETE'])(self.shutdown)

    @property
    def resource(self) -> KleinResource:
        return self._app.resource()

    @property
    def uuid(self) -> uuid.UUID:
        return self._id

    def info(self, req: Request) -> Any:
        # ensure_headers(req, {'content-type': 'application/json'})
        _write_json_response(
            request=req,
            response={'controller': f'{self._id}'},
            status_code=200
        )
        return server.NOT_DONE_YET

    def shutdown(self, req: Request) -> Any:
        ensure_headers(req, {'content-type': 'application/json'})
        _write_json_response(
            request=req,
            response={'controller': f'{self._id}'},
            status_code=200
        )
        return server.NOT_DONE_YET


class Dispatcher:
    def __init__(self):
        self._app = Klein()
        self._controllers = dict()

        # set up routes
        self._app.route('/', methods=['POST'])(self.spawn_controller)
        self._app.route('/<string:ctrl_id>', branch=True)(self.controller)

        self._app.handle_errors(MalformedRequest)(self.malformed_request)
        self._app.handle_errors(json.JSONDecodeError)(self.json_decode_error)

    @staticmethod
    def malformed_request(request: Request,
                          failure: Failure) -> Any:
        # TODO: parameterize content type
        _write_json_response(
            request=request,
            response={'error': 'Malformed request.'},
            status_code=400
        )
        return server.NOT_DONE_YET

    @staticmethod
    def json_decode_error(request: Request,
                          failure: Failure) -> Any:
        _write_json_response(
            request=request,
            response={'error': 'Could not decode JSON payload.'},
            status_code=400
        )
        return server.NOT_DONE_YET

    def run(self, host: str, port: int, reactor: PosixReactorBase) -> None:
        # Create desired endpoint
        host = host.replace(':', '\:')
        endpoint_description = f'tcp:port={port}:interface={host}'
        endpoint = endpoints.serverFromString(reactor, endpoint_description)

        # This actually starts listening on the endpoint with the Klein app
        endpoint.listen(Site(self._app.resource()))
        reactor.run()

    def spawn_controller(self, request: Request) -> Any:
        ensure_headers(request, {'content-type': 'application/json'})
        req_dict = json.load(request.content)
        try:
            controller_cls = req_dict['controller']
            parameters = req_dict['parameters']
            assert type(parameters) == dict
        except (KeyError, AssertionError):
            raise MalformedRequest()

        # TODO: make it deferred?
        # actually spawn shit
        ctrl_resource = ControllerResource()
        self._controllers[ctrl_resource.uuid] = ctrl_resource

        resp_dict = {
            'controller': str(ctrl_resource.uuid)
        }

        _write_json_response(
            request=request,
            response=resp_dict,
            status_code=200
        )
        return server.NOT_DONE_YET

    def controller(self,
                   request: Request,
                   ctrl_id: str) -> Any:
        # ensure_headers(request, {'content-type': 'application/json'})
        try:
            ctrl_id = uuid.UUID(ctrl_id)
            return self._controllers[ctrl_id].resource
        except ValueError:
            _write_json_response(
                request=request,
                response={'error': f'Malformed uuid {ctrl_id}'},
                status_code=400
            )
        except KeyError:
            _write_json_response(
                request=request,
                response={'error': f'No such controller: {ctrl_id}'},
                status_code=404
            )
        return server.NOT_DONE_YET
