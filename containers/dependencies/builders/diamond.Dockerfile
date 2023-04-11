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

#WORKDIR /tmp/install_gcc8_gpp8
#RUN wget http://mirrors.kernel.org/ubuntu/pool/universe/g/gcc-8/gcc-8_8.4.0-3ubuntu2_amd64.deb \
#    && wget http://mirrors.edge.kernel.org/ubuntu/pool/universe/g/gcc-8/gcc-8-base_8.4.0-3ubuntu2_amd64.deb \
#    && wget http://mirrors.kernel.org/ubuntu/pool/universe/g/gcc-8/libgcc-8-dev_8.4.0-3ubuntu2_amd64.deb \
#    && wget http://mirrors.kernel.org/ubuntu/pool/universe/g/gcc-8/cpp-8_8.4.0-3ubuntu2_amd64.deb \
#    && wget http://mirrors.kernel.org/ubuntu/pool/universe/g/gcc-8/libmpx2_8.4.0-3ubuntu2_amd64.deb \
#    && wget http://mirrors.kernel.org/ubuntu/pool/main/i/isl/libisl22_0.22.1-1_amd64.deb \
#    && apt-get update && apt-get -y install \
#        ./libisl22_0.22.1-1_amd64.deb \
#        ./libmpx2_8.4.0-3ubuntu2_amd64.deb \
#        ./cpp-8_8.4.0-3ubuntu2_amd64.deb \
#        ./libgcc-8-dev_8.4.0-3ubuntu2_amd64.deb \
#        ./gcc-8-base_8.4.0-3ubuntu2_amd64.deb \
#        ./gcc-8_8.4.0-3ubuntu2_amd64.deb \
#    && wget http://mirrors.kernel.org/ubuntu/pool/universe/g/gcc-8/libstdc++-8-dev_8.4.0-3ubuntu2_amd64.deb \
#    && wget http://mirrors.kernel.org/ubuntu/pool/universe/g/gcc-8/g++-8_8.4.0-3ubuntu2_amd64.deb \
#    && apt-get update && apt-get -y install \
#        ./libstdc++-8-dev_8.4.0-3ubuntu2_amd64.deb \
#        ./g++-8_8.4.0-3ubuntu2_amd64.deb \
#    && rm -rf /var/lib/apt/lists/* \
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-10 10 \
    && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-10 10 \
    && update-alternatives --auto gcc \
    && update-alternatives --auto g++

ENV CMAKE_C_COMPILER=/usr/bin/gcc-10
ENV CMAKE_CXX_COMPILER=/usr/bin/g++-10

WORKDIR /tmp/magic-diamond
RUN bash build.sh \
    --buildfolder /mrhs/dev/diamond \
    --nthreads $(nproc --all) \
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
