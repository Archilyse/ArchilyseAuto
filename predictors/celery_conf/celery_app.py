import os
import sys

import validators
from celery import Celery, signals

celery_app = Celery("predictions")
celery_app.config_from_object("predictors.celery_conf.celery_config")

scout_enabled = os.getenv("SCOUT_ENABLED", False)
in_celery_worker = sys.argv and sys.argv[0].endswith("celery") and "worker" in sys.argv

if scout_enabled and in_celery_worker:
    import scout_apm.celery
    from scout_apm.api import Config

    from predictors.tasks.utils.logging import logger

    logger.info("Scout enabled in Celery")
    Config.set(
        key=os.getenv("SCOUT_KEY"),
        name=os.getenv("SCOUT_NAME"),
        monitor=os.getenv("SCOUT_MONITOR", True),
        errors_enabled=False,
    )
    scout_apm.celery.install(celery_app)


@signals.worker_init.connect
def init_sentry(**_kwargs):
    if validators.url(os.getenv("SENTRY_DSN")):
        import sentry_sdk

        from predictors.tasks.utils.logging import logger

        logger.info("Sentry enabled")
        sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), environment="predictions-worker")
