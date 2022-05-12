FROM cmake-builder as ants

RUN apk add --no-cache libomp-dev
RUN apk add --no-cache zlib1g-dev

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
        -name DenoiseImage -or \
        -name Atropos -or \
        -name ImageMath -or \
        -name 'antsAtroposN4*' \
    \) -exec rm -rf "{}" \;

FROM build-image as mrtrix

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
        -name mrconvert -or \
        -name mrdegibbs \
    \) -exec rm -rf "{}" \;

FROM build-image AS fsl-nogpu

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

FROM nvidia-builder AS fsl-gpu

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

FROM cmake-builder AS diamond

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

FROM file-getter AS git-scilpy

WORKDIR /
RUN mkdir -p /scilpy
RUN git clone https://github.com/boiteaclou/scilpy.git /scilpy
WORKDIR /scilpy
ARG scilpy_ver=develop
RUN git fetch && git checkout --track origin/$scilpy_ver

FROM file-getter as git-mrhardi

WORKDIR /
RUN mkdir -p /mrhardi
RUN git clone https://avcaron@bitbucket.org/avcaron/magic-monkey.git /mrhardi
WORKDIR /mrhardi
ARG mrhardi_ver=develop
RUN git fetch && git checkout --track origin/$mrhardi_ver

FROM file-getter as wget-nmt-atlas

WORKDIR /
RUN wget https://afni.nimh.nih.gov/pub/dist/atlases/macaque/nmt/NMT_v2.0_asym.tgz
RUN tar -xf NMT_v2.0_asym.tgz
