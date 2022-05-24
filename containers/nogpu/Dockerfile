FROM alpine:latest AS git_cloner

RUN apk add --no-cache git

FROM git_cloner as scilpy_cloner

WORKDIR /
RUN mkdir -p /scilpy
RUN git clone https://github.com/boiteaclou/scilpy.git /scilpy
WORKDIR /scilpy
ARG scilpy_ver=develop
RUN git fetch && git checkout --track origin/$scilpy_ver

FROM git_cloner as mrhardi_cloner

WORKDIR /
RUN mkdir -p /mrhardi
RUN git clone https://avcaron@bitbucket.org/avcaron/magic-monkey.git /mrhardi
WORKDIR /mrhardi
ARG mrhardi_ver=develop
RUN git fetch && git checkout --track origin/$mrhardi_ver

FROM avcaron/mrhardi:base-nogpu

ENV MATPLOTLIBRC="/usr/local/lib/python3.7/dist-packages/matplotlib/mpl-data/"
ENV LC_ALL=en_US.utf8

RUN apt-get update && apt-get -y install \
    build-essential \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install Cython
RUN python3 -m pip install numpy
RUN python3 -m pip install setuptools==57.5.0

WORKDIR /
RUN mkdir -p /mrhs/dev/scilpy
COPY --from=scilpy_cloner /scilpy /mrhs/dev/scilpy
WORKDIR /mrhs/dev/scilpy
RUN python3 -m pip install -e .

WORKDIR /
RUN mkdir -p /mrhs/dev/mrhardi
COPY --from=mrhardi_cloner /mrhardi /mrhs/dev/mrhardi
WORKDIR /mrhs/dev/mrhardi
RUN python3 -m pip install -r requirements.txt
RUN python3 -m pip install -e .

WORKDIR /
RUN sed -i '41s/.*/backend : Agg/' /usr/local/lib/python3.7/dist-packages/matplotlib/mpl-data/matplotlibrc

RUN apt-get -y remove \
    build-essential \
    gfortran \
    g++ \
    g++-7 \
    gfortran-7
