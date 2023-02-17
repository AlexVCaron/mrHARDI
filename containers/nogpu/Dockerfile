# syntax=docker/dockerfile:1.4

FROM web_fetcher as mrhardi_cloner

WORKDIR /
RUN mkdir -p /mrhardi
RUN git clone https://github.com/AlexVCaron/mrHARDI.git /mrhardi
WORKDIR /mrhardi
ARG mrhardi_ver=develop
ARG mrhardi_is_tag=false
RUN if [ "${mrhardi_is_tag}" = "true" ] ; \
    then \
        git fetch --all --tags --force && \
        git checkout tags/$mrhardi_ver -b temp ; \
    else \
        git fetch && \
        git checkout --track origin/$mrhardi_ver ; \
    fi

WORKDIR /
RUN mkdir -p /anima
RUN wget https://github.com/Inria-Empenn/Anima-Public/releases/download/v4.2/Anima-Ubuntu-4.2.zip
RUN unzip Anima-Ubuntu-4.2.zip && \
    mv Anima-Binaries-4.2/* /anima/.

FROM scilpy_installed as nogpu

WORKDIR /
RUN mkdir -p /mrhs/dev/mrhardi
RUN mkdir -p /mrhs/dev/anima
COPY --from=mrhardi_cloner /mrhardi /mrhs/dev/mrhardi
COPY --from=mrhardi_cloner /anima /mrhs/dev/anima
WORKDIR /mrhs/dev/mrhardi
RUN python3 -m pip install -r requirements.txt
RUN python3 -m pip install -e . && \
    python3 -m pip cache purge

ENV PATH=$PATH:/anima
