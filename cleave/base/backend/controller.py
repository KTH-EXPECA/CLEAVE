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
import socket
import sys
from abc import ABC, abstractmethod
from multiprocessing import Event
from typing import Mapping

import msgpack

from ..util import PhyPropType


class Controller(ABC):
    @abstractmethod
    def process(self, sensor_values: Mapping[str, PhyPropType]) \
            -> Mapping[str, PhyPropType]:
        pass


class ControllerService(ABC):
    class NoSamplesException(Exception):
        pass

    class ShutdownException(Exception):
        pass

    def __init__(self, controller: Controller):
        super(ControllerService, self).__init__()
        self._control = controller

        self._is_running = Event()
        self._is_running.clear()

    @abstractmethod
    def listen(self):
        pass

    @abstractmethod
    def cleanup(self):
        pass

    def shutdown(self):
        self._is_running.clear()

    def serve(self):
        self._is_running.set()
        self.listen()
        while self._is_running.is_set():
            try:
                self.send_actuation(self._control.process(self.recv_samples()))
            except ControllerService.NoSamplesException:
                continue
            except ControllerService.ShutdownException:
                break

        self.cleanup()

    @abstractmethod
    def recv_samples(self) -> Mapping[str, PhyPropType]:
        pass

    @abstractmethod
    def send_actuation(self, act: Mapping[str, PhyPropType]):
        pass


class TCPControllerService(ControllerService):
    # TODO: add some logging maybe

    def __init__(self,
                 controller: Controller,
                 bind_port: int):
        super(TCPControllerService, self).__init__(controller)
        self._unpack = msgpack.Unpacker(max_buffer_size=1024)  # TODO: magic n

        self._port = bind_port
        self._server = socket.socket()
        self._client = socket.socket()

    def listen(self):
        addr = ("", self._port)  # all interfaces
        platform = sys.platform
        reuse_port = not (platform.startswith('cygwin')
                          or platform.startswith('win32'))

        if socket.has_dualstack_ipv6():
            self._server = socket.create_server(addr,
                                                family=socket.AF_INET6,
                                                dualstack_ipv6=True,
                                                reuse_port=reuse_port)
        else:
            self._server = socket.create_server(addr, reuse_port=reuse_port)

        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # TODO: change print for actual logging...
        print(f'Listening on TCP port {self._port}...')
        self._client, c_addr = self._server.accept()
        print(f'Got connection from {c_addr}.')

    def cleanup(self):
        self._client.shutdown(socket.SHUT_RDWR)
        self._client.close()
        self._server.shutdown(socket.SHUT_RDWR)
        self._server.close()

    def recv_samples(self) -> Mapping[str, PhyPropType]:
        try:
            buf = self._client.recv(1024)
            if not buf:
                raise ControllerService.NoSamplesException()

            self._unpack.feed(buf)
            return next(self._unpack)
        except StopIteration:
            raise ControllerService.NoSamplesException()
        except socket.error:
            raise ControllerService.ShutdownException()

    def send_actuation(self, act: Mapping[str, PhyPropType]):
        try:
            self._client.sendall(msgpack.packb(act, use_bin_type=True))
        except socket.error:
            raise ControllerService.ShutdownException()
