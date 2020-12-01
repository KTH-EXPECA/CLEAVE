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
from typing import Any

from klein import Klein
from twisted.internet import endpoints
from twisted.internet.posixbase import PosixReactorBase
from twisted.python.failure import Failure
from twisted.web import server
from twisted.web.http import Request
from twisted.web.server import Site


class MalformedRequest(Exception):
    pass


class Dispatcher:
    def __init__(self):
        self._app = Klein()
        self._running_ctrls = dict()

        # set up routes
        self._app.route('/', methods=['POST'])(self.spawn_controller)
        self._app.route('/<string:ctrl_id>',
                        methods=['GET'])(self.controller_info)

        self._app.handle_errors(MalformedRequest)(self.malformed_request)
        self._app.handle_errors(json.JSONDecodeError)(self.json_decode_error)

    def malformed_request(self,
                          request: Request,
                          failure: Failure) -> Any:
        # TODO: parameterize content type
        request.setResponseCode(400)
        request.write(json.dumps({
            'error': 'Malformed request.'
        }).encode('utf8'))
        request.finish()
        return server.NOT_DONE_YET

    def json_decode_error(self,
                          request: Request,
                          failure: Failure) -> Any:
        request.setResponseCode(400)
        request.write(json.dumps({
            'error': 'Could not decode JSON payload.'
        }).encode('utf8'))
        request.finish()
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
        content_type = request.getHeader('content-type').lower()
        if content_type != 'application/json':
            raise MalformedRequest()

        req_dict = json.load(request.content)
        try:
            controller_cls = req_dict['controller']
            parameters = req_dict['parameters']
            assert type(parameters) == dict
        except (KeyError, AssertionError):
            raise MalformedRequest()

        # TODO: spawn controller, store process in dictionary
        # TODO: make it deferred?
        ctrl_id = uuid.uuid4()
        self._running_ctrls[ctrl_id] = object()

        resp_dict = {
            'controller': str(ctrl_id)
        }

        request.setResponseCode(200)
        request.write(json.dumps(resp_dict).encode('utf8'))
        request.finish()
        return server.NOT_DONE_YET

    def controller_info(self,
                        request: Request,
                        ctrl_id: str) -> Any:

        ctrl_id = uuid.UUID(ctrl_id)
        try:
            controller = self._running_ctrls[ctrl_id]

            # TODO: print info
            return str(ctrl_id).encode('utf8')
        except KeyError:
            request.setResponseCode(404)
            request.finish()
            return server.NOT_DONE_YET
