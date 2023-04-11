# syntax=docker/dockerfile:1-labs

FROM web_fetcher AS template_fetcher

ADD https://afni.nimh.nih.gov/pub/dist/atlases/macaque/nmt/NMT_v2.0_asym.tgz /NMT_v2.0_asym.tgz
WORKDIR /
RUN tar -xf NMT_v2.0_asym.tgz \
    && rm -rf NMT_v2.0_asym.tgz

FROM base_image as dependencies
RUN apt-get update && apt-get -y install \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update && apt-get -y install \
    libomp-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install pip \
    && pip3 install --upgrade pip

WORKDIR /
RUN mkdir -p /mrhs/dev/diamond
RUN mkdir -p /nmt
COPY --from=diamond_builder /mrhs/dev/diamond /mrhs/dev/diamond
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_SS.nii.gz /nmt/NMT_v2.0_asym_SS.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_segmentation.nii.gz /nmt/NMT_v2.0_asym_segmentation.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_GM_cortical_mask.nii.gz /nmt/NMT_v2.0_asym_GM_cortical_mask.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/SARM_in_NMT_v2.0_asym.nii.gz /nmt/SARM_in_NMT_v2.0_asym.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/CHARM_in_NMT_v2.0_asym.nii.gz /nmt/CHARM_in_NMT_v2.0_asym.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/D99_atlas_in_NMT_v2.0_asym.nii.gz /nmt/D99_atlas_in_NMT_v2.0_asym.nii.gz
COPY --from=template_fetcher /NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_brainmask.nii.gz /nmt/NMT_v2.0_asym_brainmask.nii.gz

ENV FSLOUTPUTTYPE=NIFTI_GZ

ENV DIAMOND_BIN=/mrhs/dev/diamond/bin
ENV PATH=$DIAMOND_BIN:$PATH
