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
#   limitations under the License.

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from queue import Empty
from typing import Any, Callable, Mapping, Sequence, Set, Tuple

import msgpack
import numpy as np
from twisted.internet import task
from twisted.internet.defer import Deferred, succeed
from twisted.internet.posixbase import PosixReactorBase
from twisted.internet.protocol import DatagramProtocol
from twisted.web.client import Agent, Response, readBody
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from zope.interface import implementer

from .protocol import ControlMessageFactory, NoMessage
from ..logging import Logger
from ..recordable import NamedRecordable, Recordable, Recorder
from ...api.util import PhyPropMapping
from ...core.util import SingleElementQ


class BaseControllerInterface(Recordable, ABC):
    """
    Defines the core interface for interacting with controllers.
    """

    def __init__(self):
        self._log = Logger()

    @abstractmethod
    def put_sensor_values(self, prop_values: PhyPropMapping) -> None:
        """
        Send a sample of sensor values to the controller.

        Parameters
        ----------
        prop_values
            Mapping from property names to sensor values.
        """
        pass

    @abstractmethod
    def get_actuator_values(self) -> PhyPropMapping:
        """
        Waits for incoming data from the controller and returns a mapping
        from actuated property names to values.

        Returns
        -------
        Mapping
            Mapping from actuated property names to values.
        """
        pass


class DummyControllerInterface(BaseControllerInterface):
    def put_sensor_values(self, prop_values: PhyPropMapping) -> None:
        pass

    def get_actuator_values(self) -> PhyPropMapping:
        return {}

    @property
    def recorders(self) -> Set[Recorder]:
        return set()

    @property
    def record_fields(self) -> Sequence[str]:
        return []


class UDPControllerInterface(DatagramProtocol, BaseControllerInterface):
    """
    Controller interface which abstracts over-the-network interaction with a
    controller over UDP.
    """

    def __init__(self,
                 controller_addr: Tuple[str, int],
                 ready_callback: Callable[[BaseControllerInterface], Any]):
        super(UDPControllerInterface, self).__init__()
        self._recv_q = SingleElementQ()
        self._caddr = controller_addr
        self._msg_fact = ControlMessageFactory()
        self._waiting_for_reply = {}

        self._records = NamedRecordable(
            name=self.__class__.__name__,
            record_fields=['seq', 'send_timestamp', 'send_size'],
            opt_record_fields={'recv_timestamp': np.nan,
                               'recv_size'     : np.nan,
                               'rtt'           : np.inf}
        )

        self._ready_callback = ready_callback

    @property
    def recorders(self) -> Set[Recorder]:
        return self._records.recorders

    @property
    def record_fields(self) -> Sequence[str]:
        return self._records.record_fields

    def startProtocol(self):
        self._log.info(f'{self.__class__.__name__} listening and ready.')
        return self._ready_callback(self)

    def stopProtocol(self):
        self._log.info('Recording messages which never got a reply...')
        for _, out in self._waiting_for_reply.items():
            self._records.push_record(
                seq=out['msg'].seq,
                send_timestamp=out['msg'].timestamp,
                send_size=out['size']
            )

    def put_sensor_values(self, prop_values: PhyPropMapping) -> None:
        msg = self._msg_fact.create_sensor_message(prop_values)
        payload = msg.serialize()
        # this should always be called from the reactor thread
        self.transport.write(payload, self._caddr)
        self._waiting_for_reply[msg.seq] = {'msg' : msg,
                                            'size': len(payload)}

    def get_actuator_values(self) -> PhyPropMapping:
        try:
            return self._recv_q.pop_nowait()
        except Empty:
            return dict()

    def datagramReceived(self, datagram: bytes, addr: Tuple[str, int]):
        # unpack commands
        recv_time = time.time()
        try:
            msg = self._msg_fact.parse_message_from_bytes(datagram)
            out = self._waiting_for_reply.pop(msg.seq)

            self._records.push_record(
                seq=out['msg'].seq,
                send_timestamp=out['msg'].timestamp,
                send_size=out['size'],
                recv_timestamp=recv_time,
                recv_size=len(datagram),
                rtt=recv_time - out['msg'].timestamp
            )

            self._recv_q.put(msg.payload)
        except NoMessage:
            pass
        except KeyError:
            self._log.warn('Ignoring unprompted controller command.')
        except (ValueError, msgpack.FormatError, msgpack.StackError):
            self._log.warn('Could not unpack data from {}:{}.'.format(*addr))

    def register_with_reactor(self, reactor: PosixReactorBase):
        reactor.listenUDP(0, self)


# noinspection PyPep8Naming
@implementer(IBodyProducer)
class JSONProducer:
    def __init__(self, body: Mapping[str, Any]):
        self._ser_body = json.dumps(body,
                                    indent=None,
                                    separators=(',', ':')).encode('utf8')
        self._len = len(self._ser_body)

    @property
    def length(self) -> int:
        return self._len

    def startProducing(self, consumer):
        consumer.write(self._ser_body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class DispatcherClient:
    def __init__(self,
                 reactor: PosixReactorBase,
                 host: str,
                 port: int):
        self._dispatcher_addr = f'http://{host}:{port}'
        self._reactor = reactor
        self._agent = Agent(reactor)
        self._log = Logger()

    @property
    def dispatcher_address(self) -> str:
        return self._dispatcher_addr

    def spawn_controller(self,
                         controller: str,
                         params: Mapping[str, Any] = {}) -> Deferred:
        """
        Spawns a Controller on the Dispatcher.

        Parameters
        ----------
        controller
            The name of the desired controller class.
        params
            Parameters to pass to the controller class constructor on the
            dispatcher. All elements need to be serializable.

        Returns
        -------
            A Deferred which will eventually fire on a dictionary containing
            the details of the spawned controller.
        """

        def got_info(body: bytes):
            controller_info = json.loads(body.decode('utf8'))
            host = controller_info['host']
            port = controller_info['port']
            self._log.info(f'New controller listening on {host}:{port}.')
            return controller_info

        def info_callback(response: Response):
            if response.code == 200:
                d = readBody(response)
                d.addCallback(got_info)
            elif response.code == 202:
                # controller not yet ready
                self._log.info('Controller is not yet ready, retrying!')

                # use callLater to wait a bit
                def retry():
                    d = self._agent.request(
                        method=b'GET',
                        uri=response.request.absoluteURI,
                        headers=None, bodyProducer=None
                    )
                    d.addCallback(info_callback)
                    return d

                d = task.deferLater(self._reactor, 0.1, retry)
            else:
                raise AssertionError()  # TODO: change error type
            return d

        def resp_body_callback(body: bytes):
            controller_uid = json.loads(body.decode('utf8'))['id']
            self._log.info(f'New controller spawning: {controller_uid}')

            # find out port of the new controller
            d = self._agent.request(
                method=b'GET',
                uri=f'{self._dispatcher_addr}/{controller_uid}'.encode('utf8'),
                headers=None, bodyProducer=None
            )
            d.addCallback(info_callback)
            return d

        def spawn_callback(response: Response):
            assert 200 <= response.code < 300
            self._log.info('Received successful response to controller '
                           f'request from {self._dispatcher_addr}.')
            body_d = readBody(response)
            body_d.addCallback(resp_body_callback)
            return body_d

        # self._log.info(f'Requesting a new controller of class \"'
        #                f'{controller}\" from dispatcher listening on '
        #                f'{self._dispatcher_addr}')
        d = self._agent.request(
            method=b'POST',
            uri=self._dispatcher_addr.encode('utf8'),
            headers=Headers({'Content-Type': ['application/json']}),
            bodyProducer=JSONProducer(dict(
                controller=controller,
                params=params
            ))
        )
        d.addCallback(spawn_callback)
        return d

    def shutdown_controller(self, controller_id: str) -> Deferred:
        """
        Shuts down a controller on the dispatcher.

        Parameters
        ----------
        controller_id
            The controller to shut down.

        Returns
        -------
            A deferred which will fire once the request finishes.
        """

        def request_callback(response: Response):
            assert 200 <= response.code < 300
            self._log.info(f'Controller {controller_id} shutting down.')

        self._log.info(f'Requesting shutdown of controller {controller_id}.')
        d = self._agent.request(
            method=b'DELETE',
            uri=f'{self._dispatcher_addr}/{controller_id}'.encode('utf8'),
            headers=None, bodyProducer=None
        )
        d.addCallback(request_callback)
        return d
