SHELL := /bin/bash

.PHONY: all

all: login base cleave logout

login: FORCE
	docker login

logout: FORCE
	docker logout

base: FORCE
	docker buildx build --platform=linux/arm64,linux/amd64 -t molguin/cleave:base --target base . --push

cleave: FORCE
	docker buildx build --platform=linux/arm64,linux/amd64 -t molguin/cleave:cleave --target cleave . --push

FORCE:
