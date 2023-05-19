from celery.signals import worker_process_init

from predictors.celery_conf.celery_app import celery_app
from predictors.predictors.constants import ClassLabel
from predictors.predictors.floorplans import FloorplanPredictor, get_models
from predictors.tasks.background_mask import generate_background_shapes
from predictors.tasks.statistics import calculate_stats
from predictors.tasks.utils.celery import celery_schema
from predictors.tasks.utils.logging import logger
from predictors.tasks.utils.result_content import as_geojson, as_svg, from_geojson
from predictors.tasks.utils.serialization import (
    PredictionInputSchema,
    PredictionResultSchema,
    StatisticsResultSchema,
)


class PredictionTask(celery_app.Task):
    _models = None

    @property
    def models(self):
        if self._models is None:
            logger.info(
                "Loading ML Model in PredictionTask. This should only happen once per worker."
            )
            self._models = get_models()
        return self._models


@worker_process_init.connect
def preload_model(*args, **kwargs):
    prediction_task.models


@celery_app.task(base=PredictionTask, ignore_result=False)
@celery_schema(kwargs=PredictionInputSchema, dump=PredictionResultSchema)
def prediction_task(input_image, model, result_types, roi=None, pixels_per_meter=None):
    """Predicts the class labels and shapes for a given image using a specified predictor method.

    Args:
        input_image (np.ndarray): The input image for prediction.
        model (str): The name of the model to use for prediction.
        result_types (list): A list of result types to return (e.g., 'svg', 'json').
        roi (list, optional): A list of region of interest tuples. Defaults to None.
        pixels_per_meter (float, optional): The number of pixels per meter for scaling. Defaults to None.
    Returns:
        A dictionary containing the predicted class labels and shapes as SVG and GeoJSON.
    """
    if not roi:
        roi = [
            tuple(map(int, bbox.bounds))
            for bbox in prediction_task.models["roi"].predict(input_image)
        ]

    labels, shapes = FloorplanPredictor.predict(
        model=prediction_task.models[model],
        image=input_image,
        roi=roi,
        pixels_per_meter=pixels_per_meter,
    )

    result = {}
    if "svg" in result_types:
        result["svg"] = as_svg(labels, shapes, input_image.shape)
    if "json" in result_types:
        result["json"] = as_geojson(labels, shapes)

    return result


@celery_app.task()
@celery_schema(
    args=PredictionResultSchema(many=True, only=["json"]), dump=StatisticsResultSchema
)
def statistics_task(prediction_results):
    labels, shapes = zip(
        *[
            label_and_shape
            for result in prediction_results
            for label_and_shape in zip(*from_geojson(result["json"]))
        ]
    )
    return {
        "json": calculate_stats(labels, shapes),
    }


@celery_app.task()
@celery_schema(
    args=PredictionResultSchema(many=True, only=["json"]),
    kwargs=PredictionInputSchema(),
    dump=PredictionResultSchema,
)
def background_mask_task(prediction_results, input_image):
    shapes = [
        shape
        for result in prediction_results
        for shape in from_geojson(result["json"])[1]
    ]
    background_shapes = generate_background_shapes(input_image.shape, shapes)
    background_labels = (ClassLabel.BACKGROUND,) * len(background_shapes)
    return {
        "svg": as_svg(background_labels, background_shapes, input_image.shape),
    }
