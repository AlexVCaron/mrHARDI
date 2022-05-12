FROM light-image AS file-getter

RUN apk add --no-cache wget
RUN apk add --no-cache curl
RUN apk add --no-cache git

FROM file-getter AS cmake-builder

RUN apk add --no-cache build-essential
RUN apk add --no-cache locales
RUN apk add --no-cache libc6
RUN apk add --no-cache libc6-dev

RUN locale-gen en_US.utf8
RUN update-locale LANG=en_US.utf8

ENV LC_CTYPE=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANG=en_US.utf8
ENV LANGUAGE=en_US.utf8
ENV CMAKE_version=3.10
ENV CMAKE_build=2

WORKDIR /tmp
RUN mkdir -p cmake

WORKDIR /tmp/cmake
RUN wget https://cmake.org/files/v${CMAKE_version}/cmake-${CMAKE_version}.${CMAKE_build}.tar.gz
RUN tar -xzvf cmake-${CMAKE_version}.${CMAKE_build}.tar.gz
WORKDIR /tmp/cmake/cmake-${CMAKE_version}.${CMAKE_build}
RUN ./bootstrap
RUN make -j $(nproc --all)
RUN make install

FROM build-image as nvidia-builder

RUN NVIDIA_GPGKEY_SUM=d1be581509378368edeec8c1eb2958702feedf3bc3d17011adbf24efacce4ab5 && \
    NVIDIA_GPGKEY_FPR=ae09fe4bbd223a84b2ccfce3f60f4b3d7fa2af80 && \
    apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/7fa2af80.pub && \
    apt-key adv --export --no-emit-version -a $NVIDIA_GPGKEY_FPR | tail -n +5 > cudasign.pub && \
    echo "$NVIDIA_GPGKEY_SUM  cudasign.pub" | sha256sum -c --strict - && \
    rm cudasign.pub && \
    echo "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64 /" > /etc/apt/sources.list.d/cuda.list && \
    echo "deb https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1604/x86_64 /" > /etc/apt/sources.list.d/nvidia-ml.list && \
    apt-get purge --auto-remove -y gnupg-curl

ENV CUDA_VERSION=9.1.85
ENV CUDA_PKG_VERSION=9-1=9.1.85-1

RUN apt-get update && apt-get install -y --no-install-recommends \
    cuda-cudart-$CUDA_PKG_VERSION && \
    ln -s cuda-9.1 /usr/local/cuda && \
    rm -rf /var/lib/apt/lists/*

RUN echo "/usr/local/nvidia/lib" >> /etc/ld.so.conf.d/nvidia.conf && \
    echo "/usr/local/nvidia/lib64" >> /etc/ld.so.conf.d/nvidia.conf

ENV PATH=/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV NVIDIA_DISABLE_REQUIRE=true

RUN apt-get update && apt-get install -y --no-install-recommends \
    cuda-libraries-$CUDA_PKG_VERSION \
    cuda-npp-$CUDA_PKG_VERSION \
    cuda-cublas-9-1=9.1.85.3-1 && \
    rm -rf /var/lib/apt/lists/*
