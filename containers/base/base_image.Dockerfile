# syntax=docker.io/docker/dockerfile:1.5-labs

FROM ubuntu:jammy-20230301 AS base_image

RUN apt-get update && apt-get -y install --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    libc6 \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*.bin
