FROM python:3.9

COPY ./requirements.txt /opt/
COPY ./requirements_viz.txt /opt/

RUN pip install -U pip -Ur /opt/requirements.txt -Ur /opt/requirements_viz.txt
