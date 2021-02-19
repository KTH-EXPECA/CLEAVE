FROM ubuntu:20.04

RUN apt-get --allow-unauthenticated --allow-insecure-repositories update &&\
    apt-get --allow-unauthenticated --allow-insecure-repositories upgrade -y
RUN apt-get --allow-unauthenticated --allow-insecure-repositories install \
    build-essential gcc g++ gfortran libopenblas-base libopenblas-dev libjpeg-dev zlib1g zlib1g-dev zlibc libffi-dev \
    python3.8 python3.8-dev python3-numpy python3-matplotlib python3-scipy python3-twisted python3-pandas \
    python3-seaborn python3-click python3-pyglet -y

COPY ./requirements.txt /opt/
COPY ./requirements_viz.txt /opt/
RUN pip3 install -U pip
RUN pip3 install -r /opt/requirements.txt -r /opt/requirements_viz.txt
