# syntax=docker.io/docker/dockerfile:1.5-labs

FROM web_fetcher as mrhardi_cloner

ARG mrhardi_ver=develop

ADD https://github.com/Inria-Empenn/Anima-Public/releases/download/v4.2/Anima-Ubuntu-4.2.zip /Anima-Ubuntu-4.2.zip

WORKDIR /
RUN mkdir -p /mrhardi
ADD https://github.com/AlexVCaron/mrHARDI.git#${mrhardi_ver} /mrhardi

WORKDIR /
RUN mkdir -p /anima \
    && unzip Anima-Ubuntu-4.2.zip \
    && rm -rf Anima-Ubuntu-4.2.zip \
    && mv Anima-Binaries-4.2/* /anima/.

FROM scilpy_installed as mrhardi

WORKDIR /
RUN mkdir -p /mrhs/dev/mrhardi
RUN mkdir -p /mrhs/dev/anima
COPY --from=mrhardi_cloner /mrhardi /mrhs/dev/mrhardi
COPY --from=mrhardi_cloner /anima /mrhs/dev/anima
WORKDIR /mrhs/dev/mrhardi
RUN python3 -m pip install -r requirements.txt
RUN python3 -m pip install -e . && \
    python3 -m pip cache purge

ENV PATH=$PATH:/mrhs/dev/anima

RUN ln -s /fsl/share/fsl/bin/eddy_cuda10.2 /fsl/share/fsl/bin/eddy_cuda
