import time

from celery.signals import worker_process_init

from predictors.celery_conf.celery_app import celery_app
from predictors.tasks.logging import logger


class PredictionTask(celery_app.Task):
    _model = None

    @property
    def model(self):
        if self._model is None:
            logger.info(
                "Loading ML Model in PredictionTask. This should only happen once per worker."
            )
            self._model = load_model()
        return self._model


@worker_process_init.connect
def preload_model(*args, **kwargs):
    predict_walls_task.model


@celery_app.task(base=PredictionTask, ignore_result=False)
def predict_walls_task(image_name: str):
    from predictors.tasks.utils import download_image_and_grayscale

    predictor = predict_walls_task.model
    logger.info(f"Starting tasks predict_walls_task for image {image_name}")

    image = download_image_and_grayscale(image_name)
    labels, shapes = predictor.predict_walls(image)

    return _serialize_results(labels, shapes)


@celery_app.task(base=PredictionTask, ignore_result=False)
def predict_icons_task(image_name: str):
    from predictors.tasks.utils import download_image_and_grayscale

    predictor = predict_walls_task.model

    logger.info(f"Starting tasks predict_icons_task for image {image_name}")

    image = download_image_and_grayscale(image_name)
    labels, shapes = predictor.predict_icons(image)
    return _serialize_results(labels, shapes)


@celery_app.task(base=PredictionTask, ignore_result=False)
def predict_spaces_task(image_name: str):
    from predictors.tasks.utils import download_image_and_grayscale

    predictor = predict_walls_task.model

    logger.info(f"Starting tasks predict_icons_task for image {image_name}")

    image = download_image_and_grayscale(image_name)
    labels, shapes = predictor.predict_spaces(image)
    return _serialize_results(labels, shapes)


def load_model():
    from predictors.predictors.floorplans import FloorplanPredictor

    logger.info("Loading ML model")
    current_time = time.time()
    predictor = FloorplanPredictor()
    logger.info(f"ML model loaded in {time.time() - current_time} seconds")
    return predictor


def _serialize_results(labels, shapes):
    labels = [label.name for label in labels]
    shapes = [shape.wkt for shape in shapes]
    return tuple(labels), tuple(shapes)
