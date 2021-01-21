#!/usr/bin/env bash
#
# Copyright (c) 2021 KTH Royal Institute of Technology
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

if [ $# -lt 2 ]; then
  echo "Need to provide terminal emulator command and the number of controllers to spawn."
fi
TERM=$1
N_CTRLS=$2
CTRL_PORT=50000

# prepare docker container image
echo "Preparing docker image..."
if [[ "$(docker images -q cleave/controller:latest 2>/dev/null)" == "" ]]; then
  echo "Building image..."
  docker build -t cleave/controller:latest -f experiment_setup/controller/Dockerfile .
fi

# prepare the output folder and start the container for each controller
echo "Starting containerized controllers."
echo "To stop them, press Ctrl-C in each window."
PADDED_N=$(printf %02d "${N_CTRLS}")
for i in $(seq 1 "${N_CTRLS}"); do
  PORT=$((CTRL_PORT + i))
  PADDED_I=$(printf %02d "${i}")
  HOST_DIR="${PWD}/experiment_setup/results/${PADDED_N}_setup/controller_${PADDED_I}"
  mkdir -p "${HOST_DIR}"
  # spawn container in separate terminal window
  echo "Starting controller listening on port ${PORT}"
  (
    ${TERM} docker run --rm -t --interactive \
      --publish=${PORT}:${CTRL_PORT}/udp \
      --volume="${HOST_DIR}":/output:rw \
      cleave/controller:latest \
      cleave -vvvvv --file-log "/output/controller.log" run-controller /CLEAVE/experiment_setup/controller/config.py
  ) &
done

echo "Waiting for container processes to end"
echo "DO NOT CLOSE THIS WINDOW"
wait
echo "All containers shut down. Finishing."
