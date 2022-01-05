import itertools
import random
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from docker import DockerClient
from docker.models.containers import Container
from loguru import logger

sampling_rates_hz = (5, 10, 20, 40, 60)
delays_ms = (0, 25, 50, 100)
start_run = 1
n_runs = 10
tick_rates_hz = (120,)

base_output_dir = Path('/opt/cleave')
cleave_img = 'molguin/cleave:cleave'


@contextmanager
def docker_client(*args, **kwargs) -> Generator[DockerClient, None, None]:
    client: DockerClient = DockerClient(*args, **kwargs)
    yield client
    client.close()


def run_experiment(
        srate: int,
        delay_ms: int,
        run_idx: int,
        trate: int = 120
) -> None:
    # first thing first, create the output folder

    logger.warning(f'Running: sampling_rate={srate}, '
                   f'delay_ms={delay_ms}, '
                   f'tick_rate_hz={trate}, '
                   f'run_idx={run_idx}')

    exp_name = f'cleave_local_s{srate:03d}Hz' \
               f'_t{trate:03d}Hz' \
               f'_d{delay_ms:03d}ms'

    output_dir = (base_output_dir / exp_name).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    control_port = 50000

    with docker_client() as client:
        # start the controller
        client: DockerClient = client
        controller: Container = client.containers.run(
            detach=True,
            remove=True,
            image=cleave_img,
            command=['run-controller',
                     'examples/inverted_pendulum/controller/config.py'],
            network='bridge',
            environment={
                'PORT': control_port,
                'NAME': f'controller.run_{run_idx:02d}',
            },
            volumes=[f'{output_dir}:/opt/controller_metrics/']
        )

        # get IP of controller inside Docker network
        ctrl_addr = None
        while ctrl_addr is None or len(ctrl_addr) == 0:
            controller.reload()
            ctrl_addr = controller.attrs['NetworkSettings']['IPAddress']
            time.sleep(0.1)
        ctrl_addr = str(ctrl_addr)
        logger.warning(f'Controller address: {ctrl_addr}')

        # if delay, start the proxy
        if delay_ms > 0:
            proxy: Optional[Container] = client.containers.run(
                detach=True,
                remove=True,
                image='expeca/awsproxy:latest',
                network='bridge',
                environment={
                    'SERVERIP': ctrl_addr,
                    'DELAY'   : delay_ms // 2
                },
                cap_add='NET_ADMIN'
            )

            # get the address of the proxy
            proxy_addr = None
            while proxy_addr is None or len(ctrl_addr) == 0:
                proxy.reload()
                proxy_addr = proxy.attrs['NetworkSettings']['IPAddress']
                time.sleep(0.1)
            logger.warning(f'Proxy address: {proxy_addr}')
            ctrl_addr = proxy_addr
        else:
            proxy = None

        # run the plant
        try:
            plant = client.containers.run(
                detach=False,
                remove=True,
                image=cleave_img,
                command=['run-plant',
                         'examples/inverted_pendulum/plant/config.py'],
                network='bridge',
                environment={
                    'NAME'              : f'plant.run_{run_idx:02d}',
                    'CONTROLLER_ADDRESS': ctrl_addr,
                    'CONTROLLER_PORT'   : control_port,
                    'TICK_RATE'         : f'{trate:d}',
                    'EMU_DURATION'      : '5m',
                    'FAIL_ANGLE_RAD'    : -1,
                    'SAMPLE_RATE'       : f'{srate:d}'
                },
                volumes=[f'{output_dir}:/opt/plant_metrics/']
            )
        finally:
            # plant done, tear down controller
            controller.stop()
            if proxy is not None:
                proxy.stop()


if __name__ == '__main__':
    # create combinations of parameters
    combs = list(itertools.product(
        sampling_rates_hz,
        delays_ms,
        range(start_run, start_run + n_runs),
        tick_rates_hz
    ))

    # shuffle combinations
    random.shuffle(combs)

    # run combinations

    for params in combs:
        run_experiment(*params)
