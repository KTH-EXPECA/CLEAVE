FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ="Europe/Stockholm"

RUN apt-get update &&\
    apt-get upgrade -y
RUN apt-get install -y \
    build-essential gcc g++ gfortran libopenblas-base libopenblas-dev libjpeg-dev zlib1g zlib1g-dev zlibc libffi-dev \
    python3.8 python3.8-dev python3-numpy python3-matplotlib python3-scipy python3-twisted python3-pandas \
    python3-seaborn python3-click python3-pyglet python3-pip

COPY ./requirements.txt /opt/
COPY ./requirements_viz.txt /opt/
RUN pip3 install -U pip
RUN pip3 install -r /opt/requirements.txt -r /opt/requirements_viz.txt
