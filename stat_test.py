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

import numpy as np
import scipy.stats

from cleave.base.stats.stats import RollingStatistics

if __name__ == '__main__':
    import timeit

    stats = RollingStatistics(['test'])
    results = np.array(timeit.repeat(lambda: stats.add_sample({'test': 100}),
                                     number=1,
                                     repeat=int(1e6)))

    desc = scipy.stats.describe(results)
    mean = desc.mean
    var = desc.variance
    minv = desc.minmax[0]
    maxv = desc.minmax[1]

    print(f'Mean: {mean * 1e3:0.3f} ms | '
          f'Variance: +-{var * 1e3:0.3f} ms | '
          f'Min/Max: {minv * 1e3:0.3f} / {maxv * 1e3:0.3f}  ms')
