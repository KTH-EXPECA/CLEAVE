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
from typing import Any, Callable, Mapping, Tuple

from jsonschema import ValidationError, validate as json_validate
from twisted.web import server
from twisted.web.http import Request


#: This module contains misc utilities for the Dispatcher web server.


def write_json_response(request: Request,
                        status_code: int,
                        response: Mapping,
                        finish: bool = True) -> None:
    """
    Write a properly formatted JSON response to an HTTP request.

    Parameters
    ----------
    request
        The HTTP request.
    status_code
        Response status code.
    response
        A dictionary which will be converted to a JSON string.
    finish
        Finish the response or not.

    Returns
    -------

    """
    request.setResponseCode(status_code)
    request.setHeader('content-type', 'application/json')
    request.write(json.dumps(response).encode('utf8'))
    if finish:
        request.finish()


def json_endpoint(schema: Mapping,
                  bound_method: bool = True) \
        -> Callable[[Callable], Callable]:
    """
    Mark a method/function as an HTTP endpoint expecting JSON inputs and
    responding with JSON outputs.

    Parameters
    ----------
    schema
        Schema against which incoming requests will be validated.
    bound_method
        Whether the decorated function is a bound method or not.

    Returns
    -------
        A decorator for an endpoint callback.

    """

    def outer_wrapper(fn: Callable[..., Tuple[int, Mapping]]) -> Callable:
        def inner_wrapper(*args, **kwargs) -> Any:
            if bound_method:
                self, request, *args = args
            else:
                request, *args = args

            # ensure headers are application/json
            ctype = request.getHeader('Content-Type')
            if ctype is None or ctype.lower() != 'application/json':
                # malformed request
                write_json_response(
                    request=request,
                    response={'error': 'Content-type must be '
                                       'application/json.'},
                    status_code=415
                )
                return server.NOT_DONE_YET

            # validate the payload using json schema
            payload = json.load(request.content)
            try:
                json_validate(payload, schema)
            except ValidationError as val_err:
                write_json_response(
                    request=request,
                    response={'error': val_err.message},
                    status_code=400
                )
                return server.NOT_DONE_YET

            result = fn(self, payload, *args, **kwargs) \
                if bound_method else fn(payload, *args, **kwargs)

            if isinstance(result, Tuple):
                code, result = result
                write_json_response(
                    request=request,
                    response=result,
                    status_code=code
                )
            else:
                request.setResponseCode(result)
                request.finish()
            return server.NOT_DONE_YET

        return inner_wrapper

    return outer_wrapper
