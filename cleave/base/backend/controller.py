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
import struct
import sys
from abc import ABC, abstractmethod
from multiprocessing import Event
from typing import Mapping

import msgpack

from ..util import PhyPropType

# TODO: move this somewhere?
MAX_UDP_DGRAM_SZ_BYTES = 512


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
        addr = ('', self._port)  # all interfaces
        platform = sys.platform
        reuse_port = not (platform.startswith('cygwin')
                          or platform.startswith('win32'))

        if socket.has_dualstack_ipv6():
            self._server = socket.create_server(addr,
                                                family=socket.AF_INET6,
                                                backlog=0,
                                                dualstack_ipv6=True,
                                                reuse_port=reuse_port)
        else:
            self._server = socket.create_server(addr,
                                                backlog=0,
                                                reuse_port=reuse_port)

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


class UDPControllerService(ControllerService):
    def __init__(self,
                 controller: Controller,
                 bind_port: int):
        super(UDPControllerService, self).__init__(controller)
        self._unpack = msgpack.Unpacker(max_buffer_size=MAX_UDP_DGRAM_SZ_BYTES)
        self._struct = struct.Struct('!Bbs')
        self._port = bind_port
        self._server = socket.socket()
        self._caddr = tuple()

        # keep track of packets
        self._seq = -1
        self._prev_split_seq = -1

    def listen(self):
        addr = ('', self._port)  # all interfaces
        self._server = socket.socket(family=socket.AF_INET,
                                     type=socket.SOCK_DGRAM)
        self._server.bind(addr)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # TODO: change print for actual logging...
        print(f'Listening on UDP port {self._port}.')

    def cleanup(self):
        self._server.shutdown(socket.SHUT_RDWR)
        self._server.close()

    def recv_samples(self) -> Mapping[str, PhyPropType]:
        try:
            buf, self._caddr = self._server.recvfrom(MAX_UDP_DGRAM_SZ_BYTES)
            if not buf:
                raise ControllerService.NoSamplesException()

            (seq, split_seq, data) = self._struct.unpack(buf)

            # seq: absolute sequence number
            # split seq: split sequence number.

            exp_seq = self._seq + 1
            self._seq = seq

            if seq == exp_seq:
                # no packets dropped, nice
                if self._prev_split_seq == -1 and split_seq > 0:
                    # got a packet in a split, but we weren't expecting any
                    # just ignore it
                    raise ControllerService.NoSamplesException()

                self._prev_split_seq = split_seq
                self._unpack.feed(data)
                return next(self._unpack)
            else:
                # some packets were dropped!

                if split_seq > 0:
                    # if we missed the beginning of a sequence, need to reset
                    # unpacker and ignore subsequent split packets until a
                    # reset of the split
                    self._unpack = msgpack.Unpacker(
                        max_buffer_size=MAX_UDP_DGRAM_SZ_BYTES)
                    self._prev_split_seq = -1
                    raise ControllerService.NoSamplesException()
                elif self._prev_split_seq != -1:
                    # we were waiting for the rest of a split sequence
                    # discard what we have and start the new sequence that
                    # comes in this packet
                    self._prev_split_seq = split_seq  # it's either 0 or -1
                    self._unpack = msgpack.Unpacker(
                        max_buffer_size=MAX_UDP_DGRAM_SZ_BYTES)

                # reaching here means that split_seq was either 0 or -1 (i.e.
                # either the first packet of a split or a packet that wasn't
                # split) and thus we can just feed it to the unpacker without
                # worry.
                self._unpack.feed(data)
                return next(self._unpack)




        except StopIteration:
            raise ControllerService.NoSamplesException()
        except socket.error:
            raise ControllerService.ShutdownException()

    def send_actuation(self, act: Mapping[str, PhyPropType]):
        act_b = msgpack.packb(act, use_bin_type=True)
        rem = act_b
        packets = []
        while len(rem) > MAX_UDP_DGRAM_SZ_BYTES:
            packets.append(rem[:MAX_UDP_DGRAM_SZ_BYTES])
            rem = rem[MAX_UDP_DGRAM_SZ_BYTES:]
        packets.append(rem)

        try:
            for pckt in packets:
                self._server.sendto(pckt, self._caddr)
        except socket.error:
            raise ControllerService.ShutdownException()
