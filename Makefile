SHELL := /bin/bash

all: base cleave

base: FORCE
	docker buildx build --push --platform=linux/armhf,linux/amd64 -t molguin/cleave:base --target base . --no-cache

cleave: FORCE
	docker buildx build --push --platform=linux/armhf,linux/amd64 -t molguin/cleave:cleave --target cleave . --no-cache

FORCE:
