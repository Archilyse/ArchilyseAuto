import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import google.cloud.storage as storage
from freezegun import freeze_time

# needs to be imported to initialize the celery tasks
import predictors.tasks.prediction_tasks  # noqa 401
from app import main
from common.exceptions import InputImageException


@freeze_time("2021-01-01 00:00:00")
@patch.object(main, "uuid4", return_value="fakeuuid")
def test_get_unique_name(mock_uuid4):
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    headers = {"username": "testuser"}
    request = MockRequest(headers)
    name = main.get_unique_name(request)
    assert name == "testuser/20210101000000/fakeuuid"


@patch.object(main, "get_unique_name", return_value="dummy-image-name")
@patch.object(storage, "Blob", autospec=True)
@patch.object(storage, "Bucket", autospec=True)
def test_get_upload_url(
    mock_gcp_bucket, mock_gcp_blob, mock_get_unique_name, mock_gcp_client, api_client
):
    mock_gcp_client.from_service_account_json.return_value = mock_gcp_client
    mock_gcp_client.get_bucket.return_value = mock_gcp_bucket
    mock_gcp_bucket.blob.return_value = mock_gcp_blob
    mock_gcp_blob.generate_signed_url.return_value = "signed-url"

    response = api_client.get("/api/images/upload-url?content_type=image/png")

    assert response.status_code == 200
    assert response.json()["url"] == "signed-url"
    assert response.json()["image_name"] == "dummy-image-name"

    mock_get_unique_name.assert_called_once()
    mock_gcp_client.from_service_account_json.assert_called_once_with(
        json_credentials_path="/secrets/ml-images-bucket-access.json"
    )
    mock_gcp_client.get_bucket.assert_called_once_with(bucket_or_name="ml-images-test")
    mock_gcp_blob.generate_signed_url.assert_called_once_with(
        version="v4",
        expiration=datetime.timedelta(minutes=5),
        method="PUT",
        content_type="image/png",
        headers={
            "x-goog-content-length-range": "0,1048576",
        },
    )


@patch.object(main.Signature, "delay", return_value=MagicMock(id="fake-task-id"))
def test_request_icons_prediction(mocked_task_delay, api_client):
    response = api_client.post(
        "/api/request-prediction/icons?image_name=bla&minx=0&miny=0&maxx=1&maxy=1&pixels_per_meter=42.1"
    )
    mocked_task_delay.assert_called_once_with(
        input_image={"blob_name": "bla"},
        model="icons_v2",
        result_types=("json",),
        roi=[(0, 0, 1, 1)],
        pixels_per_meter=42.1,
    )
    assert response.status_code == 200, response.json()
    assert response.json() == {"icon_task": {"id": mocked_task_delay.return_value.id}}


@patch.object(main.Signature, "delay", return_value=MagicMock(id="fake-task-id"))
def test_request_icons_prediction_no_rois(mocked_task_delay, api_client):
    response = api_client.post(
        "/api/request-prediction/icons?image_name=bla&m&pixels_per_meter=42.1"
    )
    mocked_task_delay.assert_called_once_with(
        input_image={"blob_name": "bla"},
        model="icons_v2",
        result_types=("json",),
        roi=None,
        pixels_per_meter=42.1,
    )
    assert response.status_code == 200, response.json()
    assert response.json() == {"icon_task": {"id": mocked_task_delay.return_value.id}}


@patch.object(main.Signature, "delay", return_value=MagicMock(id="fake-task-id"))
def test_request_icons_prediction_multiple_rois(mocked_task_delay, api_client):
    response = api_client.post(
        "/api/request-prediction/icons?image_name=bla&minx=0&miny=0&maxx=1&maxy=1&minx=4&miny=4&maxx=6&maxy=6&pixels_per_meter=42.1"
    )
    mocked_task_delay.assert_called_once_with(
        input_image={"blob_name": "bla"},
        model="icons_v2",
        result_types=("json",),
        roi=[(0, 0, 1, 1), (4, 4, 6, 6)],
        pixels_per_meter=42.1,
    )
    assert response.status_code == 200, response.json()
    assert response.json() == {"icon_task": {"id": mocked_task_delay.return_value.id}}


@patch.object(main.AsyncResult, "ready", return_value=True)
@patch.object(main.AsyncResult, "get", side_effect=InputImageException)
def test_retrieve_results_invalid_input_image(
    task_is_ready, task_raises_input_image_exception, api_client
):
    prediction_results = api_client.get(
        "/api/retrieve-results/some-fake-task-id.json",
    )
    assert prediction_results.status_code == 424


@patch.object(main.AsyncResult, "ready", return_value=False)
def test_retrieve_results_task_not_ready(task_not_ready, api_client):
    prediction_results = api_client.get(
        "/api/retrieve-results/some-fake-task-id.json",
    )
    assert prediction_results.status_code == 202


@patch.object(main.AsyncResult, "ready", return_value=True)
@patch.object(main.AsyncResult, "get", return_value={"json": "some-data"})
def test_retrieve_results_content_type_does_not_exist(
    task_is_ready, task_result, api_client
):
    prediction_results = api_client.get(
        "/api/retrieve-results/some-fake-task-id.abc",
    )
    assert prediction_results.status_code == 404


@patch.object(main.AsyncResult, "ready", return_value=True)
@patch.object(
    main.AsyncResult,
    "get",
    return_value={"some-content-type": {"signed_url": "http://some-data.com"}},
)
def test_retrieve_results_task_ready(task_is_ready, task_result, api_client):
    prediction_results = api_client.get(
        "/api/retrieve-results/some-fake-task-id.some-content-type",
        follow_redirects=False,
    )
    assert prediction_results.status_code == 307
    assert prediction_results.headers["location"] == "http://some-data.com"


def test_icons_prediction(
    api_client,
    fake_bucket,
    fake_icon_predictor,
    celery_eager,
    celery_store_eager_results,
):
    # Upload an image ...
    file_upload = api_client.get(
        "/api/images/upload-url?content_type=image/jpeg"
    ).json()
    with Path("tests/fixtures/images/1.jpg").open(mode="rb") as f:
        api_client.put(file_upload["url"], files={"file": f})

    # Request a prediction ...
    prediction_task_id = api_client.post(
        "/api/request-prediction/icons?"
        f"image_name={file_upload['image_name']}&"
        "minx=0&miny=0&maxx=100&maxy=100&"
        "pixels_per_meter=40.0"
    ).json()

    # Retrieve prediction results ...
    prediction_results = api_client.get(
        f"/api/retrieve-results/{prediction_task_id['icon_task']['id']}.json",
    )

    assert prediction_results.status_code == 200
    assert prediction_results.json() == {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [75.0, 25.0],
                            [75.0, 75.0],
                            [25.0, 75.0],
                            [25.0, 25.0],
                            [75.0, 25.0],
                        ]
                    ],
                },
                "properties": {"label": "BATHTUB"},
            }
        ],
    }
