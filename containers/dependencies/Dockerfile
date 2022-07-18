# syntax=docker/dockerfile:1.4

FROM web_fetcher AS template_fetcher

WORKDIR /
RUN wget https://afni.nimh.nih.gov/pub/dist/atlases/macaque/nmt/NMT_v2.0_asym.tgz \
    && tar -xf NMT_v2.0_asym.tgz


FROM base_image as dependencies
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

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 \
    && update-alternatives --config python3 \
    && update-alternatives --set python3 /usr/bin/python3.7 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.7 1 \
    && update-alternatives --config python \
    && update-alternatives --set python /usr/bin/python3.7

RUN python3 -m pip install pip \
    && pip3 install --upgrade pip

ENV MATPLOTLIBRC="/usr/local/lib/python3.7/dist-packages/matplotlib/mpl-data/"
ENV LC_ALL=en_US.utf8
ENV PYTHONPATH="/mrhs/dev/mrtrix/lib:$PYTHONPATH"

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
    python3.7-dev \
    python3.7-tk \
    build-essential \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install Cython \
    && python3 -m pip install numpy \
    && python3 -m pip install setuptools==57.5.0

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
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_SS.nii.gz /nmt/NMT_v2.0_asym_SS.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_segmentation.nii.gz /nmt/NMT_v2.0_asym_segmentation.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_GM_cortical_mask.nii.gz /nmt/NMT_v2.0_asym_GM_cortical_mask.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/SARM_in_NMT_v2.0_asym.nii.gz /nmt/SARM_in_NMT_v2.0_asym.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/CHARM_in_NMT_v2.0_asym.nii.gz /nmt/CHARM_in_NMT_v2.0_asym.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/D99_atlas_in_NMT_v2.0_asym.nii.gz /nmt/D99_atlas_in_NMT_v2.0_asym.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_brainmask.nii.gz /nmt/NMT_v2.0_asym_brainmask.nii.gz

ENV FSLDIR=/mrhs/dev/fsl
ENV FSLOUTPUTTYPE=NIFTI_GZ

ENV FSL_BIN=$FSLDIR/bin
ENV MRTRIX_BIN=/mrhs/dev/mrtrix/bin
ENV DIAMOND_BIN=/mrhs/dev/diamond/bin
ENV ANTS_BIN=/mrhs/dev/ants/bin
ENV PATH=$ANTS_BIN:$DIAMOND_BIN:$MRTRIX_BIN:$FSL_BIN:$PATH
ENV ANTSPATH=$ANTS_BIN
