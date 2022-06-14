# syntax=docker/dockerfile:1.4

FROM base_image AS cmake_builder

RUN apt-get update && apt-get -y install \
    build-essential \
    libssl-dev \
    linux-headers-generic \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp
RUN mkdir -p cmake

ENV CMAKE_version=3.16
ENV CMAKE_build=3

WORKDIR /tmp/cmake
RUN wget https://cmake.org/files/v${CMAKE_version}/cmake-${CMAKE_version}.${CMAKE_build}.tar.gz
RUN tar -xzvf cmake-${CMAKE_version}.${CMAKE_build}.tar.gz
WORKDIR /tmp/cmake/cmake-${CMAKE_version}.${CMAKE_build}
RUN ./bootstrap
RUN make -j $(nproc --all)
RUN make install
