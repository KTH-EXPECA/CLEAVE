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

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np

sns.set(palette='Dark2')
sns.set_context('paper', font_scale=1.0)

if __name__ == '__main__':
    metrics = pd.read_csv('plant_metrics.csv')

    fig, (ax_angle, ax_pos, ax_force) = plt.subplots(ncols=1, nrows=3,
                                                     sharex='all')

    sns.lineplot(x='timestamp', y='angle', data=metrics, ax=ax_angle)
    sns.lineplot(x='timestamp', y='position', data=metrics, ax=ax_pos)

    force = metrics[~np.isclose(metrics['force'], 0.0)]
    sns.lineplot(x='timestamp', y='force', data=force, ax=ax_force)

    fig.show()
