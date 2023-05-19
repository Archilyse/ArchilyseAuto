import os
import re
from datetime import datetime, timedelta
from typing import List
from uuid import uuid4

import validators
from celery import group
from celery.canvas import Signature
from celery.result import AsyncResult
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from scout_apm.async_.starlette import ScoutMiddleware

from app.constants import ALLOWED_MIME_TYPES
from app.utils import logger
from common.bucket import get_bucket
from common.exceptions import InputImageException
from predictors.celery_conf.celery_app import celery_app

if validators.url(os.getenv("SENTRY_DSN")):
    import sentry_sdk

    logger.info("Sentry enabled in API")
    sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), environment="demo-api")

if scout_enabled := os.getenv("SCOUT_ENABLED", False):
    logger.info("Scout enabled")
    from scout_apm.api import Config

    Config.set(
        key=os.getenv("SCOUT_KEY"),
        name=os.getenv("SCOUT_NAME"),
        monitor=os.getenv("SCOUT_MONITOR", True),
    )

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # @TODO Finetune
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if scout_enabled:
    app.add_middleware(ScoutMiddleware)

input_mimetypes_regex = Query(
    regex=f"^({'|'.join(map(re.escape, ALLOWED_MIME_TYPES))})$"
)


@app.get("/api/_internal_/ping")
def api_ping():
    return "pong"


def get_unique_name(request: Request):
    username = request.headers.get("username", "unauthenticated")
    timestamp_now = datetime.now().strftime("%Y%m%d%H%M%S")
    identifier = str(uuid4())[:8]
    return f"{username}/{timestamp_now}/{identifier}"


@app.get("/api/images/upload-url")
def get_upload_url(request: Request, content_type: str = input_mimetypes_regex):
    image_name = get_unique_name(request)
    blob = get_bucket().blob(image_name)
    return {
        "url": blob.generate_signed_url(
            version="v4",
            expiration=timedelta(
                minutes=int(os.environ.get("SIGNED_URL_EXPIRATION_MINUTES", 30))
            ),
            method="PUT",
            content_type=content_type,
            headers={
                "x-goog-content-length-range": f'0,{os.getenv("MAX_FILE_SIZE")}',
            },
        ),
        "image_name": image_name,
    }


@app.post("/api/request-prediction")
def request_prediction(image_name: str):
    models = ["spaces", "walls", "icons_v1"]
    task_group = group(
        *[
            Signature(
                task="predictors.tasks.prediction_tasks.prediction_task",
                app=celery_app,
                immutable=True,
                kwargs=dict(
                    input_image={"blob_name": image_name},
                    model=model,
                    result_types=["json", "svg"],
                ),
            )
            for model in models
        ]
    ) | group(
        Signature(
            "predictors.tasks.prediction_tasks.statistics_task",
            app=celery_app,
        ),
        Signature(
            "predictors.tasks.prediction_tasks.background_mask_task",
            kwargs=dict(input_image={"blob_name": image_name}),
            app=celery_app,
        ),
    )
    statistics_result, background_result = group_result = task_group.delay()

    spaces_result, wall_result, icon_result = group_result.parent
    return {
        "wall_task": {
            "id": wall_result.id,
        },
        "icon_task": {
            "id": icon_result.id,
        },
        "spaces_task": {
            "id": spaces_result.id,
        },
        "statistics_task": {
            "id": statistics_result.id,
        },
        "background_task": {
            "id": background_result.id,
        },
    }


@app.post("/api/request-prediction/icons")
def request_icons_prediction(
    image_name: str,
    pixels_per_meter: float,
    minx: List[int] = Query(None),  # noqa B008
    miny: List[int] = Query(None),  # noqa B008
    maxx: List[int] = Query(None),  # noqa B008
    maxy: List[int] = Query(None),  # noqa B008
):
    if any(x is None for x in (minx, miny, maxx, maxy)):
        roi = None
    else:
        roi = list(zip(minx, miny, maxx, maxy))
    icon_result = Signature(
        task="predictors.tasks.prediction_tasks.prediction_task",
        app=celery_app,
    ).delay(
        input_image={"blob_name": image_name},
        model="icons_v2",
        result_types=("json",),
        roi=roi,
        pixels_per_meter=pixels_per_meter,
    )
    return {
        "icon_task": {
            "id": icon_result.id,
        },
    }


@app.get("/api/retrieve-results/{task_id}.{content_type}")
def retrieve_task_result(task_id: str, content_type: str):
    task_result = AsyncResult(id=task_id, app=celery_app)
    if task_result.ready():
        try:
            result = task_result.get(follow_parents=True)
            if signed_url := result.get(content_type, {}).get("signed_url"):
                return RedirectResponse(signed_url)
            return Response(status_code=404)
        except InputImageException:
            return Response(status_code=424)
    return Response(status_code=202)
