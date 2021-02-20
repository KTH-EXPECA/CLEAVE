FROM cleave:base_reqs

COPY . /CLEAVE
WORKDIR /CLEAVE
RUN pip3 install -U .
RUN mkdir -p /output
