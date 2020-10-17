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


# TODO: document this whole file


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
        fig.tight_layout()
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
        fig.tight_layout()
        fig.savefig(out_path / f'{fname_prefix}_actuators.png')

    plt.close('all')
    sns.reset_defaults()


def plot_client_network_metrics(metrics: pd.DataFrame,
                                out_path: str,
                                fname_prefix: str = ''):
    # plot rtt and rate?
    out_path = Path(out_path)
    assert out_path.is_dir()

    metrics = metrics.copy()
    start_time = metrics['send_timestamp'].min()

    metrics['rtt'] = metrics['recv_timestamp'] - metrics['send_timestamp']
    metrics['rtt_ms'] = metrics['rtt'] * 1000.0
    metrics['recv_timestamp_rel'] = metrics['recv_timestamp'] - start_time

    metrics['send_timestamp'] = metrics['send_timestamp'].map(
        lambda t: pd.Timestamp(t, unit='s')
    )

    metrics['recv_timestamp'] = metrics['recv_timestamp'].map(
        lambda t: pd.Timestamp(t, unit='s')
    )

    metrics['send_rate'] = metrics.rolling(window='1s',
                                           on='send_timestamp')['seq'].count()
    metrics['recv_rate'] = metrics.rolling(window='1s',
                                           on='recv_timestamp')['seq'].count()

    sns.set_theme(context='paper', palette='Dark2')
    with sns.color_palette('Dark2') as colors:
        fig, ax = plt.subplots(nrows=3)
        colors = iter(colors)

        # rtt vs time
        sns.lineplot(x='recv_timestamp_rel', y='rtt_ms', color=next(colors),
                     data=metrics, ax=ax[0])
        ax[0].set_xlabel('Time [s]')
        ax[0].set_ylabel('RTT [ms]')
        ax[0].set_title('RTT over time')

        # rtt distribution
        sns.histplot(data=metrics, x='rtt_ms', stat='density',
                     kde=True, log_scale=True,
                     color=next(colors), ax=ax[1])
        ax[1].set_title('Distribution of RTTs (milliseconds, log-scaled)')
        ax[1].set_xlabel('RTT (bins) [ms]')

        # packet rate
        sns.lineplot(x='recv_timestamp_rel', y='send_rate',
                     ax=ax[2], color=next(colors), label='Send rate',
                     data=metrics[~np.isnan(metrics['send_rate'])])
        sns.lineplot(x='recv_timestamp_rel', y='recv_rate',
                     ax=ax[2], color=next(colors), label='Receive rate',
                     data=metrics[~np.isnan(metrics['recv_rate'])])

        ax[2].set_xlabel('Time [s]')
        ax[2].set_ylabel('Packets / second')
        ax[2].set_title('Packet rates over time')
        fig.tight_layout()
        fig.savefig(out_path / f'{fname_prefix}client_metrics.png')

    plt.close('all')
    sns.reset_defaults()
