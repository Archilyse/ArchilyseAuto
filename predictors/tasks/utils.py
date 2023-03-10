import os

import cv2
import numpy as np
from google.cloud import storage


def download_image_and_grayscale(image_url: str):
    storage_client = storage.Client.from_service_account_json(
        json_credentials_path=os.getenv("ML_IMAGES_BUCKET_CREDENTIALS_FILE")
    )
    bucket = storage_client.get_bucket(
        bucket_or_name=os.getenv("AUTO_UPLOADED_IMAGES_BUCKET")
    )
    blob = bucket.blob(image_url)

    input_image = cv2.imdecode(
        np.asarray(bytearray(blob.download_as_bytes()), dtype=np.uint8), 3
    )
    image_grayscale = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
    image_grayscale = cv2.cvtColor(image_grayscale, cv2.COLOR_GRAY2BGR)
    return image_grayscale
