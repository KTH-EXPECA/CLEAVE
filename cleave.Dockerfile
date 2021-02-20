FROM cleave:base_reqs

COPY . /CLEAVE
WORKDIR /CLEAVE
RUN pip install -U .
RUN mkdir -p /output
