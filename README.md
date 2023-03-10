# Archilyse Deep Learning

Repository for the automatic inference of models from raw floor plans

## Development

### Requirements 
 * Python >= 3.10.5
 * [Google-Cloud-CLI](https://cloud.google.com/sdk/docs/install)

### Setup
 1. Install dev requirements:
    ```bash
    pip install -r requirements.txt
    ```
 2. Login to gcloud to make sure you have access to the DVC remote repository
    ```bash
    gcloud auth application-default login
    ```
 3. Pull the data (optional)
    ```bash
    dvc pull
    ```
 4. Place the GitHub deploy key in `docker/secrets/github.key` and make sure it has right permissions `chmod 400 docker/secrets/github.key`
 5. Place the gcloud service account credentials in `docker/secrets/gce_service_account_credentials.json`


### UI Demo

#### Resources needed
   1. You'll need a file named as the set variable _ML_IMAGES_BUCKET_CREDENTIALS_FILE_ in `docker/.env`.
      This file should contain the credentials for the service account that has access to the images bucket.
   2. Download necessary resources:
      ````
      make update_resources
      ````
#### Running the UI locally

   1. Install Node `16.18.0`, for example, with [nvm](https://github.com/nvm-sh/nvm#installing-and-updating):

      ```
      nvm use 16.18.0
      ```
   2. Install dev requirements:

      ```
      make install_demo_ui_requirements
      ```
   3. Run it locally:

      ```
      make run_demo_ui_locally
      ```
   
#### Running workers and api in docker

   1. download necessary resources:
       ````
      make update_resources
      ````
   2. run the workers, api and router images
      (router might be needed to be commented out if you are running the UI locally)
      ````
      make docker_build
      make docker_up
      ````
#### Authentication

   Authentication is set up using [Auth0](https://auth0.com/)
   In order for authentication to work, you need to create a copy of `.env.sample` file 
   located in the `demo/ui` directory into `.env` and fill with proper values. 

#### Tests

   Basic tests can be run with:

   ```` 
   make tests_demo_ui
   ````
### Training Workflow:

#### Changing docker image
 1. Make changes to entrypoint etc.
 2. Bump DVC_IMAGE_VERSION in .env
 3. Run `make dvc_detectron_docker_push`

#### Running a training
Run the makefile recipe `make remote_training` and you will be prompted for the relevant parameters. 
Alternatively you can use the [Vertex AI Interface](https://console.cloud.google.com/vertex-ai/training/training-pipelines?project=aurora-223611) by creating new trainings. 
Choose the `dvc_detectron` image as custom container.
Once the training is completed a new branch will be created (with a currently quite cryptic branch name) and the experiment will be available on DagsHub. For changing parameters we have two options:

#### Option 1: Custom Commit
 1. Change the config of the model under conf/detectron2/remote.yaml
 2. commit your changes and push to GitHub
 3. on Vertex AI run with flags `--train <COMMIT_HASH>`

#### Option 2: Command line arguments
 On Vertex AI, you can provide the parameters you want to override via the `-S` flag, see [Hydra Parameter Override](https://hydra.cc/docs/advanced/override_grammar/basic/) 
 and the [DVC documentation](https://hydra.cc/docs/advanced/override_grammar/basic/).
 ```
 --train_detectron <BASE_COMMIT_HASH>
 -S "conf/detectron2/remote.yaml:SOLVER.MAX_ITER=100"
 -S "conf/detectron2/remote.yaml:+INPUT.MAX_SIZE_TRAIN=800"
 -S "conf/detectron2/remote.yaml:~DATALOADER.SAMPLER_TRAIN"
 ```

#### Updating the dataset
 1. Change the config under `conf/dataset/default.yaml`
 2. commit your changes and push to GitHub
 3. on vertex AI / locally run with flags `--dataset <COMMIT_HASH>`

### GitHub Actions
In order to run the GitHub actions some variables need to be set:

#### ML_IMAGES_SA_BASE64: 

base64 encoded service account credentials for the ML images project.
In order to get it you can get the service account file (json) and run:
```
cat <FILE_NAME>.json | base64 -w 0 > temp.base_64
gh secret set ML_IMAGES_SA_BASE64 < temp.base_64
rm temp.base_64
```
This is using GitHub cli, but you can also do it manually in the GitHub secrets page.

#### DEMO_UI_ENV_BASE64:

Similar as in the previous step. We need to have the `.env` file located in the `demo/ui` directory. 
Then we can run:
```
cat demo/ui/.env | base64 -w 0 > temp.base_64
gh secret set DEMO_UI_ENV_BASE64 < temp.base_64
rm temp.base_64
```
