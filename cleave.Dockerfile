FROM molguin/cleave:base

COPY . /CLEAVE
WORKDIR /CLEAVE
RUN pip3 install -U .
RUN mkdir -p /output
