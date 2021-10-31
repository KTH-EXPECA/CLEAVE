SHELL := /bin/bash

.PHONY: all

all: base cleave

base: FORCE
	docker buildx build --output type=docker --platform=linux/armhf,linux/amd64 -t molguin/cleave:base --target base . --no-cache

cleave: FORCE
	docker buildx build --output type=docker --platform=linux/armhf,linux/amd64 -t molguin/cleave:cleave --target cleave . --no-cache

FORCE:
