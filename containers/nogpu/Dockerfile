# syntax=docker/dockerfile:1.4

FROM web_fetcher as mrhardi_cloner

WORKDIR /
RUN mkdir -p /mrhardi
RUN git clone https://avcaron@bitbucket.org/avcaron/mrhardi.git /mrhardi
WORKDIR /mrhardi
ARG mrhardi_ver=develop
RUN git fetch && git checkout --track origin/$mrhardi_ver

FROM scilpy_installed as nogpu

WORKDIR /
RUN mkdir -p /mrhs/dev/mrhardi
COPY --from=mrhardi_cloner /mrhardi /mrhs/dev/mrhardi
WORKDIR /mrhs/dev/mrhardi
RUN python3 -m pip install -r requirements.txt
RUN python3 -m pip install -e .
