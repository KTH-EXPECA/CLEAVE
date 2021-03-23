#!/bin/bash
SAMPLRATES=(10 20 25 50 100)
NPLANTS=(1 3 6 9 12)
HOSTADDRS=("192.168.0.102" "192.168.1.102")
DURATIONS=("10m")

for SRATE in ${SAMPLRATES[@]}; do
	for N in ${NPLANTS[@]}; do
		for HOST in ${HOSTADDRS[@]}; do
			for D in ${DURATIONS[@]}; do
				python util_scripts/run_centralized_experiment.py -d "$D" -s "$SRATE" -vvvvv "$HOST" "$N" "../CLEAVE_Experiments/data/experiments/5GHz_vs_ETH_NoCStates_NoHyperThreading/${D}/${HOST}/${SRATE}Hz/${N}_plants";
			done
		done
	done
done
