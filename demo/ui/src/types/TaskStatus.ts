enum TaskStatus { // https://docs.celeryq.dev/en/stable/reference/celery.result.html#celery.result.AsyncResult.status
    PENDING = "PENDING",
    STARTED = "STARTED",
    RETRY = "RETRY",
    FAILURE = "FAILURE",
    SUCCESS = "SUCCESS",
}

export default TaskStatus;
