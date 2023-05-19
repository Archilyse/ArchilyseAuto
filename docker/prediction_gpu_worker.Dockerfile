FROM ubuntu:20.04 AS darknet_builder
#Darket Yolo dependencies for ROI prediction
#Todo Make this work on GPU too...
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update \
      && apt-get install --no-install-recommends --no-install-suggests -y gnupg2 ca-certificates \
            git build-essential \
      && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/AlexeyAB/darknet.git\
      && cd darknet \
      && sed -i -e 's/LIBSO=0/LIBSO=1/g' Makefile  \
      && sed -i -e 's/OPENMP=0/OPENMP=1/g' Makefile \
      && make \
      && cp libdarknet.so /usr/local/bin \
      && cd .. && rm -rf darknet


FROM nvidia/cuda:11.2.2-cudnn8-devel-ubuntu20.04
ARG ML_IMAGES_BUCKET_CREDENTIALS_FILE

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y \
	python3-opencv ca-certificates python3-dev git wget sudo ninja-build curl
RUN ln -sv /usr/bin/python3 /usr/bin/python

RUN wget https://bootstrap.pypa.io/get-pip.py && \
	python3 get-pip.py && \
	rm get-pip.py

# install dependencies
# See https://pytorch.org/ for other options if you use a different version of CUDA
RUN pip install setuptools==59.5.0 cmake onnx  # cmake from apt-get is too old
RUN pip install torch==1.10.1 torchvision==0.11.2 -f https://download.pytorch.org/whl/cu111/torch_stable.html

RUN pip install 'git+https://github.com/facebookresearch/fvcore'
# install detectron2
RUN git clone https://github.com/facebookresearch/detectron2 detectron2_repo
# set FORCE_CUDA because during `docker build` cuda is not accessible
ENV FORCE_CUDA="1"
# This will by default build detectron2 for all common cuda architectures and take a lot more time,
# because inside `docker build`, there is no way to tell which architecture will be used.
ARG TORCH_CUDA_ARCH_LIST="Kepler;Kepler+Tesla;Maxwell;Maxwell+Tegra;Pascal;Volta;Turing"
ENV TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST}"

RUN pip install -e detectron2_repo

# Set a fixed model cache directory.
ENV FVCORE_CACHE="/tmp"

# Add Tini
ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

# Add wait-for-it
ADD https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh /usr/bin/
RUN chmod +x /usr/bin/wait-for-it.sh

#Copy resources
COPY --from=darknet_builder /usr/local/bin/libdarknet.so /usr/local/bin/libdarknet.so
COPY ./resources /code/resources/
COPY ./darknet_yolo/cfg/yolo-obj.cfg /code/resources/yolo-roi.cfg
COPY $ML_IMAGES_BUCKET_CREDENTIALS_FILE $ML_IMAGES_BUCKET_CREDENTIALS_FILE

WORKDIR /code

COPY ./predictors/requirements.txt /code/predictors/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/predictors/requirements.txt

COPY ./predictors/ /code/predictors/
COPY ./common/ /code/common/
RUN pip install --no-cache-dir --upgrade -e predictors

COPY docker/entrypoints/worker_entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/tini", "--", "/bin/bash", "/entrypoint.sh"]
