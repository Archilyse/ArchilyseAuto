import os

from google.cloud import storage


def get_bucket():
    storage_client = storage.Client.from_service_account_json(
        json_credentials_path=os.getenv("ML_IMAGES_BUCKET_CREDENTIALS_FILE")
    )
    return storage_client.get_bucket(
        bucket_or_name=os.getenv("AUTO_UPLOADED_IMAGES_BUCKET")
    )
