#!/bin/bash

# from https://stackoverflow.com/a/64799824/5035798

# get the container IP
IP=$(ifconfig eth0 | grep 'inet ' | awk '{print $2}')

# get the service name you specified in the docker-compose.yml
# by a reverse DNS lookup on the IP
SERVICE=$(dig -x $IP +short | cut -d'_' -f2)

# the number of replicas is equal to the A records
# associated with the service name
COUNT=$(dig $SERVICE +short | wc -l)

# extract the replica number from the same PTR entry
INDEX=$(dig -x $IP +short | sed 's/.*_\([0-9]*\)\..*/\1/')

# Hello I'm container 1 of 5
echo "Hello I'm container $INDEX of $COUNT"
