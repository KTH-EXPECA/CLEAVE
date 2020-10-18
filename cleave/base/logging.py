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
import sys
from typing import Dict

import loguru
from twisted.logger import ILogObserver, LogLevel, Logger, globalLogPublisher
from zope.interface import provider

# replace the default handler
loguru.logger.remove()
loguru.logger.add(sys.stderr,
                  colorize=True,
                  format='<light-green>{time}</light-green> '
                         '<level><b>{level}</b></level> '
                         '{message}')


# TODO: improve time handling.
@provider(ILogObserver)
def log_to_loguru(event: Dict) -> None:
    level = event.get('log_level', LogLevel.debug).name.upper()
    src = event.get('log_source', '')
    fmt_str = event.get('log_format', '')
    timestamp = event.get('log_time', None)

    loguru.logger.log(level, fmt_str, **event)


globalLogPublisher.addObserver(log_to_loguru)

__all__ = ['Logger']
