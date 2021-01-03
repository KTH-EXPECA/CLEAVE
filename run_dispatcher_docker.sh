#!/bin/bash
mkdir -p ./dispatcher_outputs
docker run --rm --network host --volume $PWD/dispatcher_outputs:/output:rw cleave/dispatcher:latest
