# syntax=docker.io/docker/dockerfile:1.5-labs

FROM web_fetcher as scilpy_cloner

ARG scilpy_ver=feat/subdivide_tracking_sphere
ARG dmriqcpy_ver=feat/overlay_tissue_masks

WORKDIR /
RUN mkdir -p /scilpy
ADD https://github.com/AlexVCaron/scilpy.git#${scilpy_ver} /scilpy

RUN mkdir -p /scilpy
ADD https://github.com/AlexVCaron/dmriqcpy.git#${scilpy_ver} /dmriqcpy

WORKDIR /

FROM dependencies as scilpy_installed

ENV MATPLOTLIBRC="/usr/local/lib/python3.7/dist-packages/matplotlib/mpl-data/"

RUN apt-get update && apt-get -y install \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
COPY --from=scilpy_cloner /scilpy /scilpy
WORKDIR /scilpy
RUN SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True python3.10 -m pip install -e . && \
    python3 -m pip cache purge
WORKDIR /dmriqcpy
RUN python3.10 -m pip install -e . && \
     && \
    python3.10 -m pip cache purge
