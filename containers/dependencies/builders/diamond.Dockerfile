# syntax=docker/dockerfile:1-labs

FROM cmake_builder AS diamond_builder

RUN apt-get update && apt-get -y install \
    gcc-10 \
    g++-10 \
    git \
    libomp-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /
RUN mkdir -p /mrhs/dev/diamond /tmp/install_gcc8_gpp8

ADD https://avcaron@bitbucket.org/avcaron/magic-diamond.git /tmp/magic-diamond

RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-10 10 \
    && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-10 10 \
    && update-alternatives --auto gcc \
    && update-alternatives --auto g++

ENV CMAKE_C_COMPILER=/usr/bin/gcc-10
ENV CMAKE_CXX_COMPILER=/usr/bin/g++-10

WORKDIR /tmp/magic-diamond
RUN bash build.sh \
    --buildfolder /mrhs/dev/diamond \
    --nthreads 6 \
    --itkversion 4.13.3 \
    --magic \
    --dev
WORKDIR /mrhs/dev/diamond/bin
RUN chmod 555 crlDCIEstimate
WORKDIR /mrhs/dev/diamond
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name bin \
    \) -exec rm -rf "{}" \;
