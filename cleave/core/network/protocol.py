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

import abc
import time
from dataclasses import asdict, dataclass
from enum import Enum, auto
from typing import Any, Dict, Mapping, Optional, Union

import msgpack
import msgpack_numpy as m

from ..util import PhyPropType

#: This module contains internal classes which deal with the communication
#: protocol employed in the communication between plant and controller.

__all__ = ['ControlMsgType', 'ControlMessage', 'ControlMessageFactory',
           'NoMessage']

# patch msgpack for numpy
m.patch()


class ControlMsgType(Enum):
    SENSOR_SAMPLE = auto()
    ACTUATION_CMD = auto()


# custom (de)serialization functions to handle message types
def _serialize(obj: Any) -> Any:
    if isinstance(obj, ControlMsgType):
        return {'__msgtype__': obj.value}
    return obj


def _deserialize(obj: Dict) -> Any:
    if '__msgtype__' in obj:
        return ControlMsgType(obj['__msgtype__'])
    return obj


# module-local packer and unpacker objects with some sane defaults
_packer = msgpack.Packer(
    default=_serialize
)
_unpacker = msgpack.Unpacker(
    timestamp=0,
    object_hook=_deserialize,
)


class NoMessage(Exception):
    pass


@dataclass
class ControlMessage(abc.ABC):
    msg_type: ControlMsgType
    seq: int
    timestamp: float
    payload: Any

    def serialize(self) -> bytes:
        package = asdict(self)
        return _packer.pack(package)


@dataclass
class ActuationMessage(ControlMessage):
    def __init__(self,
                 seq: int,
                 payload: Mapping[str, PhyPropType],
                 timestamp: Optional[float] = None):
        super(ActuationMessage, self).__init__(
            msg_type=ControlMsgType.ACTUATION_CMD,
            seq=seq,
            timestamp=timestamp if timestamp is not None else time.time(),
            payload=payload
        )


@dataclass
class SampleMessage(ControlMessage):
    def __init__(self,
                 seq: int,
                 payload: Mapping[str, PhyPropType],
                 timestamp: Optional[float] = None):
        super(SampleMessage, self).__init__(
            msg_type=ControlMsgType.SENSOR_SAMPLE,
            seq=seq,
            timestamp=timestamp if timestamp is not None else time.time(),
            payload=payload
        )

    def make_control_reply(self, act_cmd: Mapping[str, PhyPropType]) \
            -> ActuationMessage:
        return ActuationMessage(
            seq=self.seq,
            payload=act_cmd
        )


_msg_type_map = {
    ControlMsgType.SENSOR_SAMPLE: SampleMessage,
    ControlMsgType.ACTUATION_CMD: ActuationMessage
}


class ControlMessageFactory:
    def __init__(self):
        self._msg_count = 0

    def reset(self):
        self._msg_count = 0

    @property
    def message_count(self) -> int:
        return self._msg_count

    def create_sensor_message(self, data: Mapping[str, PhyPropType]) \
            -> SampleMessage:
        msg = SampleMessage(
            seq=self._msg_count,
            timestamp=time.time(),
            payload=data
        )

        self._msg_count += 1
        return msg

    @staticmethod
    def parse_message_from_bytes(data: bytes) -> Union[ActuationMessage,
                                                       SampleMessage]:
        _unpacker.feed(data)
        try:
            deser = next(_unpacker)

            cls = _msg_type_map[deser['msg_type']]
            return cls(seq=deser['seq'],
                       timestamp=deser['timestamp'],
                       payload=deser['payload'])
        except StopIteration:
            raise NoMessage()


class ProtocolWarning(Warning):
    pass
