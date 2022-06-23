# syntax=docker/dockerfile:1.4

FROM web_fetcher as scilpy_cloner

WORKDIR /
RUN mkdir -p /scilpy
RUN git clone https://github.com/boiteaclou/scilpy.git /scilpy
WORKDIR /scilpy
ARG scilpy_ver=develop
RUN git fetch && git checkout --track origin/$scilpy_ver


FROM dependencies as scilpy_installed

ENV MATPLOTLIBRC="/usr/local/lib/python3.7/dist-packages/matplotlib/mpl-data/"
ENV LC_ALL=en_US.utf8

WORKDIR /
RUN mkdir -p /mrhs/dev/scilpy
COPY --from=scilpy_cloner /scilpy /mrhs/dev/scilpy
WORKDIR /mrhs/dev/scilpy
RUN python3 -m pip install -e .

WORKDIR /
RUN sed -i '41s/.*/backend : Agg/' /usr/local/lib/python3.7/dist-packages/matplotlib/mpl-data/matplotlibrc

RUN apt-get -y remove \
    build-essential \
    gfortran \
    g++ \
    g++-7 \
    gfortran-7
