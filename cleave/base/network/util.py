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
import struct
from typing import Tuple, Union

_pack_str_udp = '!Bbs'  # seq: uint8, split_seq: int8, data: bytes
_struct_packer = struct.Struct(_pack_str_udp)


def prepare_udp_payload(payload: Union[bytes, bytearray],
                        max_dgram_sz: int) -> Tuple[bytes]:
    hdr_sz = _struct_packer.size
    if len(payload) + hdr_sz > max_dgram_sz:
        rem = payload
        dgrams = []

    else:
        return
