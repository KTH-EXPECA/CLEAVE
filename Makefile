SHELL := /bin/bash

all: base cleave push

base: FORCE
	docker buildx build --platform=linux/armhf,linux/amd64 -t molguin/cleave:base --target base .

cleave: FORCE
	docker buildx build --platform=linux/armhf,linux/amd64 -t molguin/cleave:cleave --target cleave .

push: push_base push_cleave

push_base: FORCE
	docker push molguin/cleave:base

push_cleave: FORCE
	docker push molguin/cleave:cleave

FORCE:
