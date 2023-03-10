FROM ubuntu:20.04 AS darknet_builder
#Darket Yolo dependencies for ROI prediction
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


FROM python:3.8.12-slim

# Add Tini
ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

# Add wait-for-it
ADD https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh /usr/bin/
RUN chmod +x /usr/bin/wait-for-it.sh

RUN apt-get update && apt-get install -y ninja-build gcc g++ git
RUN pip install torch==1.10.1+cpu torchvision==0.11.2+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html
RUN pip install 'git+https://github.com/facebookresearch/detectron2.git'


COPY ./predictors/requirements.txt /code/predictors/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/predictors/requirements.txt

COPY --from=darknet_builder /usr/local/bin/libdarknet.so /usr/local/bin/libdarknet.so