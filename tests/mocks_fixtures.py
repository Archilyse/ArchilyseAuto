from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.main import app


@pytest.fixture
def celery_eager(monkeypatch):
    from predictors.celery_conf import celery_config

    monkeypatch.setattr(celery_config, "task_always_eager", True)


@pytest.fixture
def celery_store_eager_results(monkeypatch):
    from predictors.celery_conf import celery_config

    monkeypatch.setattr(celery_config, "task_store_eager_result", True)


@pytest.fixture
def api_client():
    from starlette.testclient import TestClient

    return TestClient(app)


@pytest.fixture
def mock_gcp_client(monkeypatch):
    from google.cloud import storage

    mock_client = MagicMock(spec=storage.Client)
    monkeypatch.setattr(storage, "Client", mock_client)

    return mock_client


@pytest.fixture
def test_file_server(tmpdir_factory):
    from fastapi import File, UploadFile
    from fastapi.responses import FileResponse

    tempdir = str(tmpdir_factory.mktemp("test_data"))

    @app.put(tempdir, status_code=201)
    def upload(file_name, file: UploadFile = File(...)):  # noqa B008
        try:
            contents = file.file.read()
            Path(tempdir, file_name).parent.mkdir(exist_ok=True, parents=True)
            with open(Path(tempdir, file_name), "wb") as f:
                f.write(contents)
        except Exception:
            return {"message": "There was an error uploading the file"}, 500
        finally:
            file.file.close()

    @app.get(tempdir)
    def download(file_name):
        return FileResponse(Path(tempdir, file_name))

    return tempdir


@pytest.fixture
def fake_bucket(test_file_server, monkeypatch):
    class FakeBlob:
        def __init__(self, blob_name):
            self.blob_name = blob_name

        def upload_from_string(self, content, content_type):
            with open(Path(test_file_server, self.blob_name), mode="w") as f:
                f.write(content)

        def upload_from_file(self, content, content_type):
            with open(Path(test_file_server, self.blob_name), mode="wb") as f:
                f.write(content)

        def download_as_string(self):
            with open(Path(test_file_server, self.blob_name), mode="r") as f:
                return f.read()

        def download_as_bytes(self):
            with open(Path(test_file_server, self.blob_name), mode="rb") as f:
                return f.read()

        def generate_signed_url(self, *args, **kwargs):
            return f"{test_file_server}?file_name={self.blob_name}"

    class FakeBucket:
        def blob(self, name):
            return FakeBlob(name)

    import app.main
    import predictors.tasks.utils.storage

    monkeypatch.setattr(app.main, "get_bucket", FakeBucket)
    monkeypatch.setattr(predictors.tasks.utils.storage, "get_bucket", FakeBucket)


@pytest.fixture
def fake_predictor():
    from shapely.geometry import box

    from predictors.predictors.base import BasePredictor
    from predictors.predictors.constants import ClassLabel

    def fake_predict(image):
        h, w = image.shape[:2]
        return (ClassLabel.BATHTUB,), (box(w * 0.25, h * 0.25, w * 0.75, h * 0.75),)

    predictor = MagicMock(spec=BasePredictor)
    predictor.predict.side_effect = fake_predict
    return predictor


@pytest.fixture
def fake_icon_predictor(fake_predictor, monkeypatch):
    import predictors.tasks.prediction_tasks

    monkeypatch.setattr(
        predictors.tasks.prediction_tasks,
        "get_models",
        lambda: {"icons_v2": fake_predictor},
    )
