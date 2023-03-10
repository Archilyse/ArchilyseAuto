import os
from datetime import datetime
from uuid import uuid4

import aiohttp
import cv2
import numpy as np
import validators
from celery.result import AsyncResult
from fastapi import FastAPI, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from gcloud.aio.storage import Storage
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from app.stats import calculate_stats
from app.utils import (
    _get_labels_shapes_from_tasks,
    as_svg,
    deserialize_tasks_results,
    logger,
)
from predictors.celery_conf.celery_app import celery_app
from predictors.predictors.utils.geometry import get_polygons
from predictors.tasks.prediction_tasks import (
    predict_icons_task,
    predict_spaces_task,
    predict_walls_task,
)

if validators.url(os.getenv("SENTRY_DSN")):
    import sentry_sdk

    logger.info("Sentry enabled")
    sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), environment="demo-api")


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # @TODO Finetune
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def upload_image(image: UploadFile, image_name):
    image_bytes = await image.read()
    async with aiohttp.ClientSession() as session:
        storage = Storage(
            service_file=os.getenv("ML_IMAGES_BUCKET_CREDENTIALS_FILE"),
            session=session,
        )
        await storage.upload(
            os.getenv("AUTO_UPLOADED_IMAGES_BUCKET"), image_name, image_bytes
        )


@app.get("/api/_internal_/ping")
def api_ping():
    return "pong"


@app.post("/api/request_prediction")
async def request_prediction(request: Request, image: UploadFile):
    username = request.headers.get("username", "unauthenticated")
    image_name = (
        f"{username}-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{str(uuid4())[:8]}"
    )
    await upload_image(image=image, image_name=image_name)

    spaces_task_result = predict_spaces_task.s().apply_async([image_name])
    wall_task_result = predict_walls_task.s().apply_async([image_name])
    icon_task_result = predict_icons_task.s().apply_async([image_name])
    return {
        "wall_task": {"id": wall_task_result.id, "status": wall_task_result.status},
        "icon_task": {"id": icon_task_result.id, "status": icon_task_result.status},
        "spaces_task": {
            "id": spaces_task_result.id,
            "status": spaces_task_result.status,
        },
    }


@app.get("/api/retrieve_prediction/{task_id}")
async def retrieve_prediction(task_id: str):
    task_result = AsyncResult(id=task_id, app=celery_app)
    if task_result.ready():
        input_image = await _download_image(task_result.args[0])
        labels, shapes = deserialize_tasks_results(*task_result.get())
        return StreamingResponse(
            as_svg(input_image, labels, shapes), media_type="image/svg"
        )
    else:
        return {"status": task_result.status}


@app.post("/api/retrieve_stats")
async def retrieve_stats(request: Request):
    body = await request.json()
    wall_task_id = body.get("walls_task_id")
    icon_task_id = body.get("icons_task_id")
    space_task_id = body.get("spaces_task_id")
    try:
        labels, shapes = _get_labels_shapes_from_tasks(
            task_ids=[wall_task_id, icon_task_id, space_task_id]
        )
    except ValueError as e:
        return {"status": "NOT READY", "error": str(e)}

    return {"status": "READY", "statistics": calculate_stats(labels, shapes)}


@app.post("/api/retrieve_background")
async def retrieve_background(request: Request):
    from predictors.predictors.constants import ClassLabel

    BUFFER_PX = 40
    UNBUFFER_PX = 40

    body = await request.json()
    task_ids = body.get("tasks")
    _, shapes = _get_labels_shapes_from_tasks(task_ids=task_ids)
    input_image = await _get_input_image_from_task(task_id=task_ids[0])

    image_bbox = box(0, 0, *input_image.shape[:2][::-1])

    # First we buffer/unbuffer the geometries to remove gaps between them
    shapes_union = (
        unary_union(shapes)
        .buffer(BUFFER_PX, cap_style=3, join_style=2)
        .buffer(-UNBUFFER_PX, cap_style=3, join_style=2)
    )

    # Then we only keep only the shell of the unary union to remove holes in them,
    # thus we have the shell of all geometries
    shapes_union_polygon_exterior = [
        Polygon(shell=polygon.exterior)  # nosec
        for polygon in get_polygons(shapes_union)
    ]

    # Then we remove this shell from the entire image
    background_shapes = tuple(
        get_polygons(image_bbox.difference(unary_union(shapes_union_polygon_exterior)))
    )
    background_labels = (ClassLabel.BACKGROUND,) * len(background_shapes)

    return StreamingResponse(
        as_svg(input_image, background_labels, background_shapes),
        media_type="image/svg",
    )


async def _download_image(image_url: str):
    async with aiohttp.ClientSession() as session:
        storage = Storage(
            service_file=os.getenv("ML_IMAGES_BUCKET_CREDENTIALS_FILE"),
            session=session,
        )
        image_bytes = await storage.download(
            os.getenv("AUTO_UPLOADED_IMAGES_BUCKET"), image_url
        )
        return cv2.imdecode(np.asarray(bytearray(image_bytes), dtype=np.uint8), 3)


async def _get_input_image_from_task(task_id: str):
    task_result = AsyncResult(id=task_id, app=celery_app)
    input_image = await _download_image(task_result.args[0])
    return input_image
