# syntax=docker/dockerfile:1.4

FROM base_image as fsl_builder

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
