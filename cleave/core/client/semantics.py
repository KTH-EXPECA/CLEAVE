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
import abc
from typing import Generic, SupportsBytes, SupportsFloat, SupportsInt, Type, \
    TypeVar

T = TypeVar('T', int, float, bool, bytes)


class BaseSemanticVariable(Generic[T],
                           SupportsFloat,
                           SupportsInt,
                           SupportsBytes,
                           abc.ABC):
    """
    Base class for semantically significant variables in a State.
    """

    def __init__(self, value: T, record: bool = True):
        self._value = value
        self._record = record

    def get_value(self) -> T:
        return self._value

    def set_value(self, value: T):
        self._value = value

    def get_type(self) -> Type:
        return type(self._value)

    @property
    def record(self) -> bool:
        return self._record

    def __float__(self) -> float:
        return float(self._value)

    def __int__(self) -> int:
        return int(self._value)

    def __bytes__(self) -> bytes:
        return bytes(self._value)
