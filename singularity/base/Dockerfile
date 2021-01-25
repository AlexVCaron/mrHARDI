FROM nvidia/cuda:9.1-runtime-ubuntu16.04 AS base

RUN apt-get update && apt-get -y install \
    locales \
    libc6 \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*.bin
RUN locale-gen en_US.utf8
RUN update-locale LANG=en_US.utf8

ENV LC_CTYPE=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANG=en_US.utf8
ENV LANGUAGE=en_US.utf8

# Build Cmake base
FROM base AS cmake_base

ENV CMAKE_version=3.10
ENV CMAKE_build=2

RUN apt-get update && apt-get -y install \
    build-essential \
    linux-headers-generic \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp
RUN mkdir -p cmake

WORKDIR /tmp/cmake
RUN wget https://cmake.org/files/v${CMAKE_version}/cmake-${CMAKE_version}.${CMAKE_build}.tar.gz
RUN tar -xzvf cmake-${CMAKE_version}.${CMAKE_build}.tar.gz
WORKDIR /tmp/cmake/cmake-${CMAKE_version}.${CMAKE_build}
RUN ./bootstrap
RUN make -j $(nproc --all)
RUN make install

# Build FSL
FROM base AS fsl_builder

RUN apt-get update && apt-get -y install \
    libgl1-mesa-dev \
    linux-headers-generic \
    python \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
RUN mkdir -p /mms/dev
WORKDIR /tmp
RUN mkdir -p fsl_sources

WORKDIR /tmp/fsl_sources
RUN wget https://fsl.fmrib.ox.ac.uk/fsldownloads/fslinstaller.py
RUN python fslinstaller.py -d /mms/dev/fsl -D
WORKDIR /mms/dev/fsl
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name bin -or \
        -name lib -or \
        -name etc -or \
        -name extras -or \
        -name data \
    \) -exec rm -rf "{}" \;
WORKDIR /mms/dev/fsl/bin
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name 'eddy*' -or \
        -name topup -or \
        -name bet -or \
        -name bet2 -or \
        -name applytopup -or \
        -name fslmaths \
    \) -exec rm -rf "{}" \;
WORKDIR /mms/dev/fsl/extras
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name bin -or \
        -name lib \
    \) -exec rm -rf "{}" \;
WORKDIR /mms/dev/fsl/etc
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name flirtsch -or \
        -name lib \
    \) -exec rm -rf "{}" \;

# Build Mrtrix
FROM base AS mrtrix_builder

RUN apt-get update && apt-get -y install \
    build-essential \
    clang \
    git \
    libeigen3-dev \
    libfftw3-dev \
    libgl1-mesa-dev \
    libomp-dev \
    libpng-dev \
    libqt4-opengl-dev \
    libtiff5-dev \
    linux-headers-generic \
    python \
    python-numpy \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
RUN mkdir -p /mms/dev/mrtrix
WORKDIR /mms/dev
RUN git clone https://github.com/MRtrix3/mrtrix3.git mrtrix
WORKDIR /mms/dev/mrtrix
RUN ./configure -nogui -openmp
RUN ./build
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -wholename './bin' -or \
        -wholename './bin/*' -or \
        -wholename './lib' -or \
        -wholename './lib/libmrtrix*' \
    \) -exec rm -rf "{}" \;
WORKDIR /mms/dev/mrtrix/bin
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name dwi2fod -or \
        -name dwi2response -or \
        -name dwi2tensor -or \
        -name dwidenoise -or \
        -name mrdegibbs \
    \) -exec rm -rf "{}" \;

# Build Diamond
FROM cmake_base AS diamond_builder

RUN apt-get update && apt-get -y install \
    git \
    libomp-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
RUN mkdir -p /mms/dev/diamond
COPY diamond_package.tar.gz /tmp/
WORKDIR /tmp
RUN mkdir -p diamond
RUN tar -xzf /tmp/diamond_package.tar.gz -C /tmp/diamond

WORKDIR /tmp/diamond
RUN ./build.sh --buildfolder /mms/dev/diamond --nthreads $(nproc --all)
WORKDIR /mms/dev/diamond/bin
RUN chmod 111 crlDCIEstimate
WORKDIR /mms/dev/diamond
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name bin \
    \) -exec rm -rf "{}" \;

# Build ANTs
FROM cmake_base AS ants_builder

RUN apt-get update && apt-get -y install \
    git \
    libomp-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
RUN mkdir -p /mms/dev
WORKDIR /mms/dev
RUN git clone https://github.com/cookpa/antsInstallExample.git ants
WORKDIR /mms/dev/ants
RUN chmod 777 installANTs.sh
RUN ./installANTs.sh
RUN rm -rf ANTs/ build/ LICENSE README.md installANTs.sh
RUN mv install/* .
RUN rm -rf install
WORKDIR /mms/dev/ants/bin
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name antsRegistration -or \
        -name 'antsRegistrationSyN*' -or \
        -name N4BiasFieldCorrection -or \
        -name antsApplyTransforms -or \
        -name antsMotionCorr -or \
        -name antsMotionCorrDiffusionDirection -or \
        -name DenoiseImage \
    \) -exec rm -rf "{}" \;

# Build final image
FROM base
WORKDIR /
RUN mkdir -p /mms/dev/fsl
RUN mkdir -p /mms/dev/mrtrix
RUN mkdir -p /mms/dev/diamond
RUN mkdir -p /mms/dev/ants
COPY --from=fsl_builder /mms/dev/fsl /mms/dev/fsl
COPY --from=mrtrix_builder /mms/dev/mrtrix /mms/dev/mrtrix
COPY --from=diamond_builder /mms/dev/diamond /mms/dev/diamond
COPY --from=ants_builder /mms/dev/ants /mms/dev/ants

ENV FSL_BIN=/mms/dev/fsl/bin
ENV MRTRIX_BIN=/mms/dev/mrtrix/bin
ENV DIAMOND_BIN=/mms/dev/diamond/bin
ENV ANTS_BIN=/mms/dev/ants/bin
ENV PATH=$ANTS_BIN:$DIAMOND_BIN:$MRTRIX_BIN:$FSL_BIN:$PATH

RUN apt-get update && apt-get -y install \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*
RUN add-apt-repository ppa:deadsnakes/ppa

RUN apt-get update && apt-get -y install \
    libblas-dev \
    libeigen3-dev \
    liblapack-dev \
    libfftw3-dev \
    libgl1-mesa-dev \
    libomp-dev \
    libqt4-opengl-dev \
    libtiff5-dev \
    linux-headers-generic \
    zlib1g-dev \
    python3-pip \
    python3.7 \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1
RUN update-alternatives --config python3
RUN update-alternatives --set python3 /usr/bin/python3.7

RUN python3 -m pip install pip
RUN pip3 install --upgrade pip

RUN apt-get update && apt-get -y install \
    python3.7-dev \
    python3.7-tk \
    && rm -rf /var/lib/apt/lists/*
