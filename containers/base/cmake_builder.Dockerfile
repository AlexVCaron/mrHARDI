# syntax=docker/dockerfile:1-labs

FROM base_image AS cmake_builder

RUN apt-get update && apt-get -y install \
    build-essential \
    libssl-dev \
    linux-headers-generic \
    && rm -rf /var/lib/apt/lists/*

ENV CMAKE_version=3.16
ENV CMAKE_build=3

ADD https://cmake.org/files/v${CMAKE_version}/cmake-${CMAKE_version}.${CMAKE_build}.tar.gz /tmp/cmake.tar.gz
WORKDIR /tmp
RUN tar -xzf cmake.tar.gz \
    && rm -rf cmake.tar.gz
WORKDIR /tmp/cmake-${CMAKE_version}.${CMAKE_build}
RUN ./bootstrap
RUN make -j 6
RUN make install
