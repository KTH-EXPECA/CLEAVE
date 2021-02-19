FROM cleave:base_reqs

COPY . /CLEAVE
RUN pip install -U pip -Ur /CLEAVE/requirements.txt -Ur /CLEAVE/requirements_viz.txt
RUN mkdir -p /output
