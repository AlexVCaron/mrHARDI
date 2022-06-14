# syntax=docker/dockerfile:1.4

FROM nogpu as nvidia

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gcc-6 \
    g++-6 && \
    rm -rf /var/lib/apt/lists/*


WORKDIR /tmp
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-6 10 && \
    update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-6 10 && \
    update-alternatives --set gcc /usr/bin/gcc-6 && \
    update-alternatives --set g++ /usr/bin/g++-6 && \
    curl -LO https://developer.nvidia.com/compute/cuda/9.1/Prod/local_installers/cuda_9.1.85_387.26_linux && \
    curl -LO https://developer.nvidia.com/compute/cuda/9.1/Prod/patches/1/cuda_9.1.85.1_linux && \
    curl -LO https://developer.nvidia.com/compute/cuda/9.1/Prod/patches/2/cuda_9.1.85.2_linux && \
    curl -LO https://developer.nvidia.com/compute/cuda/9.1/Prod/patches/3/cuda_9.1.85.3_linux && \
    sh cuda_9.1.85_387.26_linux --silent --override --toolkit && \
    sh cuda_9.1.85.1_linux --silent --accept-eula && \
    sh cuda_9.1.85.2_linux --silent --accept-eula && \
    sh cuda_9.1.85.3_linux --silent --accept-eula && \
    rm /tmp/cuda_9.1.85*_linux && \
    update-alternatives --remove-all gcc && \
    update-alternatives --remove-all g++ && \
    apt-get remove -y build-essential curl gcc-6 g++-6

RUN echo "/usr/local/nvidia/lib" >> /etc/ld.so.conf.d/nvidia.conf && \
    echo "/usr/local/nvidia/lib64" >> /etc/ld.so.conf.d/nvidia.conf && \
    echo "/usr/local/cuda-9.1/lib64" >> /etc/ld.so.conf.d/cuda-9.1.conf

ENV PATH=$PATH:/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

RUN ln -s /mrhs/dev/fsl/bin/eddy_cuda9.1 /mrhs/dev/fsl/bin/eddy_cuda
