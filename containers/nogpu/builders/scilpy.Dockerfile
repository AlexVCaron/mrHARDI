# syntax=docker/dockerfile:1.4

FROM web_fetcher as scilpy_cloner

WORKDIR /
RUN mkdir -p /scilpy
RUN git clone https://github.com/boiteaclou/scilpy.git /scilpy
WORKDIR /scilpy
ARG scilpy_ver=develop
ARG scilpy_is_tag=false
RUN if [[ -z "${scilpy_is_tag}" ]] ; \
    then \
        git fetch --all --tags --force && \
        git checkout --track tags/$scilpy_ver -b temp ; \
    else \
        git fetch && \
        git checkout --track origin/$scilpy_ver ; \
    fi

FROM dependencies as scilpy_installed

ENV MATPLOTLIBRC="/usr/local/lib/python3.7/dist-packages/matplotlib/mpl-data/"
ENV LC_ALL=en_US.utf8

WORKDIR /
RUN mkdir -p /mrhs/dev/scilpy
COPY --from=scilpy_cloner /scilpy /mrhs/dev/scilpy
WORKDIR /mrhs/dev/scilpy
RUN python3 -m pip install -e . && \
    python3 -m pip cache purge

WORKDIR /
RUN sed -i '41s/.*/backend : Agg/' /usr/local/lib/python3.7/dist-packages/matplotlib/mpl-data/matplotlibrc

RUN apt-get -y remove \
    build-essential \
    gfortran \
    g++ \
    g++-7 \
    gfortran-7
