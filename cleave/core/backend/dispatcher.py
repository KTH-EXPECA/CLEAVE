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
from typing import Any

import klein
from twisted.internet.posixbase import PosixReactorBase
from twisted.python.failure import Failure
from twisted.web.http import Request


class MalformedRequest(Exception):
    pass


class Dispatcher:
    def __init__(self):
        self._app = klein.Klein()
        self._running_ctrls = dict()

        # set up routes
        self._app.route('/', methods=['POST'])(self.spawn_controller)
        self._app.handle_errors(MalformedRequest)(self.malformed_request)
        self._app.handle_errors(json.JSONDecodeError)(self.json_decode_error)

    def malformed_request(self,
                          request: Request,
                          failure: Failure) -> Any:
        # TODO: parameterize content type
        request.setResponseCode(400)
        return {
            'error': 'Malformed request.'
        }

    def json_decode_error(self,
                          request: Request,
                          failure: Failure) -> Any:
        request.setResponseCode(400)
        request.finish()
        return {
            'error': 'Could not decode JSON payload.'
        }

    # def run(self, host: str, port: int, reactor: PosixReactorBase) -> None:
    #     # Create desired endpoint
    #     endpoint_description = f'tcp4:port={port}:interface={host}'
    #     endpoint = endpoints.serverFromString(reactor, endpoint_description)
    #
    #     # This actually starts listening on the endpoint with the Klein app
    #     endpoint.listen(Site(app.resource())
    #
    #     # After doing other things like setting up logging,
    #     # starting other services in the reactor or
    #     # listening on other ports or sockets:
    #     reactor.run()

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

        request.setResponseCode(200)
        return req_dict
