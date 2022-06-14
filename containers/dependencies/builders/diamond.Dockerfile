# syntax=docker/dockerfile:1.4

FROM cmake_builder AS diamond_builder

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
