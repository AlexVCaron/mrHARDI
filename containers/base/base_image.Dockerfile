# syntax=docker/dockerfile:1.4

FROM ubuntu:18.04 AS base_image

RUN apt-get update && apt-get -y install --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    locales \
    libc6 \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*.bin
RUN locale-gen en_US.utf8
RUN update-locale LANG=en_US.utf8

ENV LC_CTYPE=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANG=en_US.utf8
ENV LANGUAGE=en_US.utf8
