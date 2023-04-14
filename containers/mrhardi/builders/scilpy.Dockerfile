# syntax=docker/dockerfile:1-labs

FROM web_fetcher as scilpy_cloner

ARG scilpy_ver=develop

WORKDIR /
RUN mkdir -p /scilpy
ADD https://github.com/boiteaclou/scilpy.git#${scilpy_ver} /scilpy
WORKDIR /scilpy

FROM dependencies as scilpy_installed

ENV MATPLOTLIBRC="/usr/local/lib/python3.7/dist-packages/matplotlib/mpl-data/"
ENV LC_ALL=en_US.utf8

RUN apt-get update && apt-get -y install \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
RUN mkdir -p /mrhs/dev/scilpy
COPY --from=scilpy_cloner /scilpy /mrhs/dev/scilpy
WORKDIR /mrhs/dev/scilpy
RUN SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True python3.10 -m pip install -e . && \
    python3 -m pip cache purge
