import os
import uuid
from datetime import timedelta

from marshmallow import EXCLUDE, Schema, fields, validates
from marshmallow.exceptions import ValidationError
from marshmallow.validate import Length

from common.exceptions import InputImageException
from predictors.tasks.utils.image import decode_image_bytes, greyscale_image
from predictors.tasks.utils.storage import download_blob, upload_blob

SIGNED_URL_EXPIRATION = timedelta(
    minutes=int(os.environ.get("SIGNED_URL_EXPIRATION_MINUTES", 30))
)


def _download_image(image_url, content_type):
    image_bytes = download_blob(image_url, content_type)
    try:
        if (image := decode_image_bytes(image_bytes)) is not None:
            return greyscale_image(image)
    except Exception as ex:
        raise InputImageException(f"{image_url} could not be loaded.") from ex
    raise InputImageException(f"{image_url} could not be loaded.")


class BlobStore(fields.Field):
    def __init__(
        self,
        upload=None,
        download=None,
        content_type=None,
        signed_url=False,
        signed_url_expiration=None,
        **additional_metadata,
    ):
        super().__init__(**additional_metadata)
        self.signed_url = signed_url
        self.signed_url_expiration = signed_url_expiration
        self.upload = upload
        self.download = download
        self.content_type = content_type

    def _serialize(self, value, attr, obj, **kwargs):
        return self.upload(
            blob_name=str(uuid.uuid4()),
            content=value,
            content_type=self.content_type,
            signed_url=self.signed_url,
            signed_url_expiration=self.signed_url_expiration,
        )

    def _deserialize(self, value, attr, data, **kwargs):
        return self.download(value["blob_name"], self.content_type)


class BaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE


class PredictionResultSchema(BaseSchema):
    svg = BlobStore(
        upload=upload_blob,
        content_type="image/svg+xml",
        signed_url=True,
        signed_url_expiration=SIGNED_URL_EXPIRATION,
        dump_only=True,
        required=False,
    )
    json = BlobStore(
        upload=upload_blob,
        download=download_blob,
        content_type="application/json",
        signed_url=True,
        signed_url_expiration=SIGNED_URL_EXPIRATION,
        required=False,
    )


class PredictionInputSchema(BaseSchema):
    VALID_RESULT_TYPES = {"svg", "json"}

    input_image = BlobStore(download=_download_image)
    result_types = fields.List(fields.Str(), validate=Length(min=1))
    pixels_per_meter = fields.Float(required=False)
    roi = fields.List(
        fields.Tuple([fields.Int()] * 4),
        required=False,
        allow_none=True,
    )

    @validates("result_types")
    def validate_result_types(self, value):
        if not all(result_type in self.VALID_RESULT_TYPES for result_type in value):
            raise ValidationError(
                f"result_types must be part of {self.VALID_RESULT_TYPES}."
            )


class StatisticsResultSchema(BaseSchema):
    json = BlobStore(
        upload=upload_blob,
        content_type="application/json",
        signed_url=True,
        signed_url_expiration=SIGNED_URL_EXPIRATION,
    )
