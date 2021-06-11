FROM alpine:latest AS git_cloner

RUN apk add --no-cache git

WORKDIR /
RUN mkdir -p /scilpy
RUN mkdir -p /mmy
RUN git clone https://github.com/boiteaclou/scilpy.git /scilpy
WORKDIR /scilpy
RUN git fetch && git checkout --track origin/develop
WORKDIR /
RUN git clone https://avcaron@bitbucket.org/avcaron/magic-monkey.git /mmy
WORKDIR /mmy
RUN git fetch && git checkout --track origin/devflow

FROM avcaron/magic-monkey:base-latest
WORKDIR /
RUN mkdir -p /mms/dev/scilpy
RUN mkdir -p /mms/dev/magic-monkey
COPY --from=git_cloner /scilpy /mms/dev/scilpy
COPY --from=git_cloner /mmy /mms/dev/magic-monkey

ENV MATPLOTLIBRC="/usr/local/lib/python3.7/dist-packages/matplotlib/mpl-data/"
ENV LC_ALL=en_US.utf8

RUN apt-get update && apt-get -y install \
    build-essential \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install Cython
RUN python3 -m pip install numpy

WORKDIR /mms/dev/magic-monkey
RUN python3 -m pip install -r requirements.txt
RUN python3 -m pip install -e .

WORKDIR /mms/dev/scilpy
RUN python3 -m pip install -e .

WORKDIR /
RUN sed -i '41s/.*/backend : Agg/' /usr/local/lib/python3.7/dist-packages/matplotlib/mpl-data/matplotlibrc

RUN apt-get -y remove \
    build-essential \
    gfortran \
    g++ \
    g++-5 \
    gfortran-5
