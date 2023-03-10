import os

import validators
from celery import Celery, signals

celery_app = Celery("predictions")
celery_app.config_from_object("predictors.celery_conf.celery_config")


@signals.worker_init.connect
def init_sentry(**_kwargs):
    if validators.url(os.getenv("SENTRY_DSN")):
        import sentry_sdk

        from predictors.tasks.logging import logger

        logger.info("Sentry enabled")
        sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), environment="predictions-worker")
