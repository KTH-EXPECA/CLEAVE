DOCKERCMD := docker --config .docker buildx build --platform=linux/arm64,linux/amd64
SHELL := /bin/bash

REPO := expeca/cleave

SRC_DIR := .../cleave
SRC_FILES := $(wildcard $(SRC_DIR)/*)

.PHONY: all

all: base cleave

base: Dockerfile $(SRC_FILES) cleave.py
	$(DOCKERCMD) -t $(REPO):base -f $< --target base . --push

cleave: Dockerfile $(SRC_FILES) cleave.py
	$(DOCKERCMD) -t $(REPO):cleave -f $< --target cleave . --push
