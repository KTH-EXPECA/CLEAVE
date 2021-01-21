FROM python:3.8

# copy the current working dir
COPY . /CLEAVE
WORKDIR /CLEAVE
RUN pip install -U .

RUN mkdir -p /output
WORKDIR /output

#CMD cleave -vvvvv run-controller /CLEAVE/experiment_setup/controller/config.py
