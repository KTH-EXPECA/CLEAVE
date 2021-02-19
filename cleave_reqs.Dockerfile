FROM python:3.9

RUN apt-get update && apt-get upgrade -y
RUN apt-get install build-essential gcc g++ gfortran libopenblas-base libopenblas-dev libjpeg-dev zlib1g zlib1g-dev zlibc -y

COPY ./requirements.txt /opt/
COPY ./requirements_viz.txt /opt/

RUN pip install --global-option="build -j4" -U pip -Ur /opt/requirements.txt -Ur /opt/requirements_viz.txt
