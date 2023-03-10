#FROM daisukekobayashi/darknet:cpu
FROM daisukekobayashi/darknet:gpu-cc80
#cc80 is optimized for the gpu A100 https://arnon.dk/matching-sm-architectures-arch-and-gencode-for-various-nvidia-cards/
RUN apt-get update && apt-get install -y unzip
COPY darknet_yolo/ /workspace
WORKDIR /workspace

RUN unzip data/labels.zip -d data/
RUN rm data/labels.zip

ENTRYPOINT bash