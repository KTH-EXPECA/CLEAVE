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
#

if [ $# -lt 2 ]; then
  echo "Need to provide controller host and plant index."
fi

CTRL_HOST=$1
PLANT_N=$2
PADDED_N=$(printf %02d "${PLANT_N}")
LOG="./plant_${PADDED_N}.log"

CLEAVE_CONTROL_HOST="${CTRL_HOST}" \
  CLEAVE_PLANT_INDEX="${PLANT_N}" \
  python cleave.py -vvvvv -f "${LOG}" run-plant experiment_setup/plant/config.py
