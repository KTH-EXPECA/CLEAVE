DOCKER := docker buildx build
REPO := expeca/cleave
BUILD_ARM64 := $(DOCKER) --platform=linux/arm64
BUILD_AMD64 := $(DOCKER) --platform=linux/amd64

SRC_DIR := .../cleave
SRC_FILES := $(wildcard $(SRC_DIR)/*)

.PHONY: all base-multiarch cleave-multiarch base-amd64 base-arm64 cleave-amd64 cleave-arm64

all: base-multiarch cleave-multiarch
base-multiarch: base-amd64 base-arm64
cleave-multiarch: cleave-amd64 cleave-arm64

base-arm64: Dockerfile $(SRC_FILES) cleave.py
	$(BUILD_ARM64) -t $(REPO):base -f $< --target base .

base-amd64: Dockerfile $(SRC_FILES) cleave.py
	$(BUILD_AMD64) -t $(REPO):base -f $< --target base .

cleave-arm64: Dockerfile $(SRC_FILES) cleave.py
	$(BUILD_ARM64) -t $(REPO):cleave -f $< --target cleave .

cleave-amd64: Dockerfile $(SRC_FILES) cleave.py
	$(BUILD_AMD64) -t $(REPO):cleave -f $< --target cleave .
