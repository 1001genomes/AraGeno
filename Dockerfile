FROM python:2.7
MAINTAINER Ümit Seren

ENV PYTHONUNBUFFERED 1

RUN mkdir /code
WORKDIR /code
VOLUME /code

ADD requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt && pip install gunicorn

ARG HPC_USER
ENV HPC_USER=${HPC_USER}

RUN mkdir -p /root/.ssh
RUN echo "Host *\nUser ${HPC_USER}\n"> /root/.ssh/config


