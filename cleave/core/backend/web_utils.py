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
from typing import Any, Mapping

from twisted.python.failure import Failure
from twisted.web import server
from twisted.web.http import Request


class MalformedRequest(Exception):
    pass


def write_json_response(request: Request,
                        status_code: int,
                        response: Mapping,
                        finish: bool = True) -> None:
    request.setResponseCode(status_code)
    request.setHeader('content-type', 'application/json')
    request.write(json.dumps(response).encode('utf8'))
    if finish:
        request.finish()


def malformed_request(request: Request,
                      failure: Failure) -> Any:
    # TODO: parameterize content type
    write_json_response(
        request=request,
        response={'error': 'Malformed request.'},
        status_code=400
    )
    return server.NOT_DONE_YET


def json_decode_errback(request: Request,
                        failure: Failure) -> Any:
    write_json_response(
        request=request,
        response={'error': 'Could not decode JSON payload.'},
        status_code=400
    )
    return server.NOT_DONE_YET


def ensure_headers(req: Request, headers: Mapping[str, str]) -> None:
    for header, exp_value in headers.items():
        req_value = req.getHeader(header)
        if req_value is None or req_value.lower() != exp_value.lower():
            raise MalformedRequest()
