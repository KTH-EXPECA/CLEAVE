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
import time
from multiprocessing import Event
from typing import Callable, Dict, Optional, Tuple

from loguru import logger


def execute_periodically(fn: Callable[[...], None],
                         period: float,
                         args: Optional[Tuple] = None,
                         kwargs: Optional[Dict] = None,
                         shutdown_flag: Event = Event()):
    shutdown_flag.clear()
    while not shutdown_flag.is_set():
        ti = time.time()
        fn(*args, **kwargs)
        dt = time.time() - ti
        try:
            time.sleep(period - dt)
        except ValueError:
            logger.warning('Function {} execution took longer than given '
                           'period! dt = {}, period = {}',
                           fn.__name__, dt, period, enqueue=True)
