# Training

In order to train you need to prepare the image, build and push. Then you can run it on Vertex AI.
Steps:
1. you need to make sure the images and labels and generated and stored in the darknet_yolo/data folder.
In order to do that run 
```
make yolo_prepare_data_folder
```
2. This should run the dvc step to generate labels (filtering based on blacklisted, etc...) then copy the labels and images corresponding to the labels to the darknet_yolo/data folder.
It will also generate the train.txt and test.txt files. It should download automatically also the initial weights from gcs.
3. Build the docker image and push it. In order to do that run
```
make yolo_build
make yolo_push
```
4. Run the training job on Vertex AI. It should run automatically with no params.
Tested with an A100 with 64 batch size 8 subdivisions and 608x608 resolution. This should work and cause no out of memory errors.


## Configuring the training job
The important things to configure are
- backup folder: where the weights will be saved. This is located in obj.data. Example: "/gcs/archilyse_darknet_yolo/6k-iter-a100/" (gcs is always present on vertex ai and gives you access to the buckets)
- batch: the batch size. This is located in yolo-obj.cfg. Decrease if you get out of memory errors
- subdivisions: the number of subdivisions. This is located in yolo-obj.cfg. Decrease if you get out of memory errors
- width & height: This is located in yolo-obj.cfg. Decrease if you get out of memory errors
- max_batches: This is located in yolo-obj.cfg.
More info can be found in the [darknet repo](https://github.com/AlexeyAB/darknet) and [docker-repo](https://github.com/daisukekobayashi/darknet-docker), but this could be useful links:
- https://stackoverflow.com/questions/50390836/understanding-darknets-yolo-cfg-config-files
- https://medium.com/analytics-vidhya/train-a-custom-yolov4-object-detector-using-google-colab-61a659d4868#4be1
- https://robocademy.com/2020/05/01/a-gentle-introduction-to-yolo-v4-for-object-detection-in-ubuntu-20-04/

# Local predictions
Once you have trained the model, you can run local predictions. In order to do that you need to 
1. Download the weights from the bucket. You specified that as the backup folder in the training job.
2. To run the prediction you can use the following command:
```
docker run --runtime=nvidia --rm -v $PWD:/workspace -w /workspace daisukekobayashi/darknet:gpu \
darknet detector test data/obj.data cfg/yolo-obj.cfg computed.weights -i 0 -thresh 0.25 data/obj/image.jpg -ext_output
```
You have to run this command from the darknet_yolo folder.
Place the desired image in the darknet_yolo folder (so that it is availble in the container) and change the name accordingly.
You should substitute computed.weights with the name of the weights file you downloaded.
This will run the prediction and the results will be available in darknet_yolo/predictions.jpg. 
You can change also play with the threshold value.
