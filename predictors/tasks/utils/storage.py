import io
import json
from datetime import timedelta
from typing import Any, Optional, Union

from common.bucket import get_bucket


def download_blob(blob_name: str, content_type: Optional[str] = None):
    blob = get_bucket().blob(blob_name)
    if content_type == "application/json":
        return json.loads(blob.download_as_string())
    return blob.download_as_bytes()


def upload_blob(
    blob_name: str,
    content: Union[io.BytesIO, Any],
    content_type: Optional[str] = None,
    signed_url: bool = False,
    signed_url_expiration: Optional[timedelta] = None,
):
    blob = get_bucket().blob(blob_name)
    if content_type == "application/json":
        blob.upload_from_string(json.dumps(content), content_type=content_type)
    else:
        blob.upload_from_file(content, content_type=content_type)

    blob_urls = {"blob_name": blob_name}
    if signed_url:
        blob_urls["signed_url"] = blob.generate_signed_url(
            expiration=signed_url_expiration
        )
    return blob_urls
