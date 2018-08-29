FROM ubuntu:16.04

ADD . /htc
WORKDIR /htc

RUN apt-get update && apt-get install -y python-pip python-dev
RUN cd /htc && pip install -r requirements.pip
# RUN echo "/h"
ENV PYTHONPATH="/htc":PYTHONPATH

