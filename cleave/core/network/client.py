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

import builtins
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from queue import Empty
from typing import Any, Mapping, Tuple

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
from ..client.control import BaseControllerInterface
from ..logging import Logger
from ..recordable import CSVRecorder, NamedRecordable
from ...api.util import PhyPropMapping
from ...core.util import SingleElementQ


class RecordingUDPControlClient(DatagramProtocol, ABC):

    def __init__(self,
                 controller_addr: Tuple[str, int],
                 output_dir: Path):
        super(RecordingUDPControlClient, self).__init__()
        self._recv_q = SingleElementQ()
        self._caddr = controller_addr
        self._msg_fact = ControlMessageFactory()
        self._waiting_for_reply = {}
        self._log = Logger()

        self._records = NamedRecordable(
            name=self.__class__.__name__,
            record_fields=['seq', 'send_timestamp', 'send_size'],
            opt_record_fields={'recv_timestamp': np.nan,
                               'recv_size'     : np.nan,
                               'rtt'           : np.inf}
        )
        self._recorder = CSVRecorder(recordable=self._records,
                                     output_dir=output_dir,
                                     metric_name='udpclient')

    @abstractmethod
    def on_start(self, control_i: BaseControllerInterface):
        pass

    @abstractmethod
    def on_end(self):
        pass

    def startProtocol(self):
        self._recorder.initialize()

        # build a controller interface
        class ControllerInterface(BaseControllerInterface):
            proto = self

            def put_sensor_values(self, prop_values: PhyPropMapping) -> None:
                msg = self.proto._msg_fact.create_sensor_message(prop_values)
                payload = msg.serialize()
                # this should always be called from the reactor thread
                try:
                    self.proto.transport.write(payload, self.proto._caddr)
                except builtins.BlockingIOError:
                    # Handles bug https://twistedmatrix.com/trac/ticket/2790
                    # in twisted, where EWOULDBLOCK or EAGAIN are raised when
                    # the UDP socket buffer is full.
                    # Simply ignoring the datagram works, since UDP doesn't
                    # provide any guarantees anyway.
                    self.proto._log.warn('Full UDP socket buffer, silently '
                                         'dropping datagram.')
                self.proto._waiting_for_reply[msg.seq] = {'msg' : msg,
                                                          'size': len(payload)}

            def get_actuator_values(self) -> PhyPropMapping:
                try:
                    return self.proto._recv_q.pop_nowait()
                except Empty:
                    return dict()

        self._log.info(f'UDP client listening and ready.')
        self.on_start(ControllerInterface())

    def stopProtocol(self):
        self.on_end()
        self._log.info('Recording messages that never got a reply...')
        for _, out in self._waiting_for_reply.items():
            self._records.push_record(
                seq=out['msg'].seq,
                send_timestamp=out['msg'].timestamp,
                send_size=out['size']
            )
        self._recorder.shutdown()

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
