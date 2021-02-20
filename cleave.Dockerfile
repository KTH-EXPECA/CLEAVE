FROM cleave:base_reqs

COPY . /CLEAVE
RUN pip install -U pip -r /CLEAVE/requirements.txt -r /CLEAVE/requirements_viz.txt
RUN mkdir -p /output
