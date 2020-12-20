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

from __future__ import annotations

spawn_controller = {
    '$schema'    : 'http://json-schema.org/draft-07/schema#',
    'title'      : 'Spawn controller',
    'description': 'A request to spawn a controller.',
    'type'       : 'object',
    'properties' : {
        'controller': {
            'description': 'The controller class to instantiate.',
            'type'       : 'string'
        },
        'params'    : {
            'description': 'The parameters provided to the controller on '
                           'instantiation.',
            'type'       : 'object'
        },
    },
    'required'   : ['controller']
}

shutdown_controller = {
    '$schema'    : 'http://json-schema.org/draft-07/schema#',
    'title'      : 'Shut down controller',
    'description': 'A request to shut down a controller safely.',
    'type'       : 'object',
    'properties' : {
        'id': {
            'description': 'The id of the controller to be shut down.',
            'type'       : 'string'
        }
    },
    'required'   : ['id']
}
