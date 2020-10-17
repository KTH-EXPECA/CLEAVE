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
from pathlib import Path
from typing import Any, Collection, Iterator

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes


def __plot_raw_proc_values(df: pd.DataFrame,
                           var_name: str,
                           prefix: str,
                           colors: Iterator[Any],
                           proc_label: str,
                           ax: Axes):
    raw = f'{prefix}{var_name}_raw'
    proc = f'{prefix}{var_name}_proc'

    raw_values = df[~np.isnan(df[raw])]
    proc_values = df[~np.isnan(df[proc])]
    sns.lineplot(x='timestamp', y=raw, color=next(colors),
                 data=raw_values,
                 label='Raw Value',
                 ax=ax)
    sns.lineplot(x='timestamp', y=proc, color=next(colors),
                 data=proc_values,
                 label=proc_label,
                 ax=ax)

    ax.set_ylabel(var_name)
    ax.set_xlabel('Time [s]')


def plot_plant_metrics(metrics: pd.DataFrame,
                       sens_vars: Collection[str],
                       act_vars: Collection[str],
                       out_path: str,
                       fname_prefix: str = ''):
    out_path = Path(out_path)
    assert out_path.is_dir()

    metrics = metrics.copy()

    # use relative timestamp
    metrics['timestamp'] = metrics['timestamp'] - metrics['timestamp'].min()

    sns.set_theme(context='paper', palette='Dark2')
    with sns.color_palette('Dark2', len(metrics.columns)) as colors:
        colors = iter(colors)
        # sensor readings
        fig, ax = plt.subplots(nrows=len(sens_vars),
                               sharex='all',
                               squeeze=False)
        for ax, var in zip(ax, sens_vars):
            __plot_raw_proc_values(df=metrics,
                                   var_name=var,
                                   prefix='sens_',
                                   colors=colors,
                                   proc_label='Sensor Reading',
                                   ax=ax.item())
        fig.suptitle('Monitored values & sensor readings')
        fig.savefig(out_path / f'{fname_prefix}_sensors.png')

        # actuator outputs
        fig, ax = plt.subplots(nrows=len(act_vars),
                               sharex='all',
                               squeeze=False)
        for ax, var in zip(ax, act_vars):
            __plot_raw_proc_values(df=metrics,
                                   var_name=var,
                                   prefix='act_',
                                   colors=colors,
                                   proc_label='Actuator Output',
                                   ax=ax.item())
        fig.suptitle('Actuated values & actuator outputs')
        fig.savefig(out_path / f'{fname_prefix}_actuators.png')
    sns.reset_defaults()
