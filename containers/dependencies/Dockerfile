FROM ubuntu:18.04 AS base

RUN apt-get update && apt-get -y install --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
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

# Build FSL
FROM base AS fsl_builder

RUN apt-get update && apt-get -y install \
    libgl1-mesa-dev \
    linux-headers-generic \
    python \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
RUN mkdir -p /mrhs/dev
WORKDIR /tmp
RUN mkdir -p fsl_sources

WORKDIR /tmp/fsl_sources
RUN wget https://fsl.fmrib.ox.ac.uk/fsldownloads/fslinstaller.py
RUN python fslinstaller.py -d /mrhs/dev/fsl -D
WORKDIR /mrhs/dev/fsl
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name bin -or \
        -name lib -or \
        -name etc -or \
        -name extras -or \
        -name data \
    \) -exec rm -rf "{}" \;
WORKDIR /mrhs/dev/fsl/bin
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name applytopup -or \
        -name bet -or \
        -name bet2 -or \
        -name betsurf -or \
        -name convert_xfm -or \
        -name eddy -or \
        -name eddy_cuda -or \
        -name eddy_cuda9.1 -or \
        -name eddy_openmp -or \
        -name fast -or \
        -name flirt -or \
        -name fslhd -or \
        -name fslmaths -or \
        -name fslmerge -or \
        -name fslroi -or \
        -name fslstats -or \
        -name fslval -or \
        -name imcp -or \
        -name immv -or \
        -name imtest -or \
        -name remove_ext -or \
        -name standard_space_roi -or \
        -name topup \
    \) -exec rm -rf "{}" \;
WORKDIR /mrhs/dev/fsl/extras
RUN find . -maxdepth 1 -not \( \
        -name . -or \
        -name .. -or \
        -name bin -or \
        -name lib \
    \) -exec rm -rf "{}" \;
WORKDIR /mrhs/dev/fsl/etc
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
RUN mkdir -p /mrhs/dev/mrtrix
WORKDIR /mrhs/dev
RUN git clone https://github.com/MRtrix3/mrtrix3.git mrtrix
WORKDIR /mrhs/dev/mrtrix
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

# Build Diamond
FROM cmake_base AS diamond_builder

RUN apt-get update && apt-get -y install \
    git \
    libomp-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
RUN mkdir -p /mrhs/dev/diamond

WORKDIR /tmp
RUN git clone https://avcaron@bitbucket.org/avcaron/magic-diamond.git /tmp/magic-diamond

WORKDIR /tmp/magic-diamond
RUN bash build.sh \
    --buildfolder /mrhs/dev/diamond \
    --nthreads $(nproc --all) \
    --magic \
    --dev
WORKDIR /mrhs/dev/diamond/bin
RUN chmod 111 crlDCIEstimate
WORKDIR /mrhs/dev/diamond
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
RUN mkdir -p /mrhs/dev
WORKDIR /mrhs/dev
RUN git clone https://github.com/cookpa/antsInstallExample.git ants
WORKDIR /mrhs/dev/ants
RUN chmod 777 installANTs.sh
RUN ./installANTs.sh
RUN rm -rf ANTs/ build/ LICENSE README.md installANTs.sh
RUN mv install/* .
RUN rm -rf install
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

FROM alpine:latest AS file_wget

RUN apk add --no-cache wget

WORKDIR /
RUN wget https://afni.nimh.nih.gov/pub/dist/atlases/macaque/nmt/NMT_v2.0_asym.tgz
RUN tar -xf NMT_v2.0_asym.tgz

# Build final image
FROM base
WORKDIR /
RUN mkdir -p /mrhs/dev/fsl
RUN mkdir -p /mrhs/dev/mrtrix
RUN mkdir -p /mrhs/dev/diamond
RUN mkdir -p /mrhs/dev/ants
RUN mkdir -p /nmt
COPY --from=fsl_builder /mrhs/dev/fsl /mrhs/dev/fsl
COPY --from=mrtrix_builder /mrhs/dev/mrtrix /mrhs/dev/mrtrix
COPY --from=diamond_builder /mrhs/dev/diamond /mrhs/dev/diamond
COPY --from=ants_builder /mrhs/dev/ants /mrhs/dev/ants
COPY --from=file_wget /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_SS.nii.gz /nmt/NMT_v2.0_asym_SS.nii.gz
COPY --from=file_wget /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_segmentation.nii.gz /nmt/NMT_v2.0_asym_segmentation.nii.gz
COPY --from=file_wget /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_GM_cortical_mask.nii.gz /nmt/NMT_v2.0_asym_GM_cortical_mask.nii.gz
COPY --from=file_wget /NMT_v2.0_asym/NMT_v2.0_asym/SARM_in_NMT_v2.0_asym.nii.gz /nmt/SARM_in_NMT_v2.0_asym.nii.gz
COPY --from=file_wget /NMT_v2.0_asym/NMT_v2.0_asym/CHARM_in_NMT_v2.0_asym.nii.gz /nmt/CHARM_in_NMT_v2.0_asym.nii.gz
COPY --from=file_wget /NMT_v2.0_asym/NMT_v2.0_asym/D99_atlas_in_NMT_v2.0_asym.nii.gz /nmt/D99_atlas_in_NMT_v2.0_asym.nii.gz
COPY --from=file_wget /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_brainmask.nii.gz /nmt/NMT_v2.0_asym_brainmask.nii.gz

ENV FSLDIR=/mrhs/dev/fsl
ENV FSLOUTPUTTYPE=NIFTI_GZ

ENV FSL_BIN=/mrhs/dev/fsl/bin
ENV MRTRIX_BIN=/mrhs/dev/mrtrix/bin
ENV DIAMOND_BIN=/mrhs/dev/diamond/bin
ENV ANTS_BIN=/mrhs/dev/ants/bin
ENV PATH=$ANTS_BIN:$DIAMOND_BIN:$MRTRIX_BIN:$FSL_BIN:$PATH
ENV ANTSPATH=$ANTS_BIN

RUN apt-get update && apt-get -y install \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update && apt-get -y install \
    bc \
    dc \
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

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
    python3.7-dev \
    python3.7-tk \
    && rm -rf /var/lib/apt/lists/*
