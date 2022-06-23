# syntax=docker/dockerfile:1.4

FROM cmake_builder as ants_builder

RUN apt-get update && apt-get -y install \
    git \
    libomp-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
RUN mkdir ants_build &&\
    git clone https://github.com/ANTsX/ANTs.git
WORKDIR /ANTs
RUN git fetch --tags &&\
    git checkout tags/v2.3.4 -b v2.3.4
WORKDIR /ants_build
RUN cmake \
    -DBUILD_SHARED_LIBS=OFF \
    -DUSE_VTK=OFF \
    -DSuperBuild_ANTS_USE_GIT_PROTOCOL=OFF \
    -DBUILD_TESTING=OFF \
    -DRUN_LONG_TESTS=OFF \
    -DRUN_SHORT_TESTS=OFF \
    -DCMAKE_INSTALL_PREFIX=/mrhs/dev/ants \
    ../ANTs && \
    make -j $(nproc --all)
WORKDIR /ants_build/ANTS-build
RUN make install
WORKDIR /mrhs/dev/ants/bin
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name antsRegistration -or \
        -name 'antsRegistrationSyN*' -or \
        -name N4BiasFieldCorrection -or \
        -name antsApplyTransforms -or \
        -name antsMotionCorr -or \
        -name antsMotionCorrDiffusionDirection -or \
        -name DenoiseImage -or \
        -name Atropos -or \
        -name ImageMath -or \
        -name 'antsAtroposN4*' \
    \) -exec rm -rf "{}" \;
