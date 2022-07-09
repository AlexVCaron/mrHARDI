# syntax=docker/dockerfile:1.4

FROM base_image as mrtrix_builder

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
RUN mkdir -p /mrhs/dev/mrtrix
WORKDIR /mrhs/dev
RUN git clone https://github.com/MRtrix3/mrtrix3.git mrtrix
WORKDIR /mrhs/dev/mrtrix
RUN git fetch --all --tags && git checkout tags/3.0.3 -b mrtrix3.0.3-branch
RUN ./configure -nogui -openmp
RUN ./build
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -wholename './bin' -or \
        -wholename './bin/*' -or \
        -wholename './lib' -or \
        -wholename './lib/*' \
        -wholename './share/' \
        -wholename './share/*' \
    \) -exec rm -rf "{}" \;
WORKDIR /mrhs/dev/mrtrix/bin
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name dwi2fod -or \
        -name dwi2response -or \
        -name dwi2tensor -or \
        -name dwidenoise -or \
        -name mrconvert -or \
        -name mrdegibbs \
    \) -exec rm -rf "{}" \;
