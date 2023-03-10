import glob
import os
from pathlib import Path

from google.cloud import storage
from google.oauth2.credentials import Credentials

GOOGLE_TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
RETRY_MAX_ATTEMPTS = 5
RETRY_TIME_MULTIPLIER = 3
RETRY_MAX_TIME = 10


class GCloudStorageHandler:
    def __init__(
        self,
        project_id=None,
        client_id=None,
        client_secret=None,
        refresh_token=None,
        bucket_name=None,
    ):
        self._client = None
        self.project_id = project_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.bucket_name = bucket_name

    @property
    def client(self):
        if not self._client:
            self._client = storage.Client(
                project=self.project_id,
                credentials=Credentials(
                    token=None,
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    refresh_token=self.refresh_token,
                    token_uri=GOOGLE_TOKEN_URL,
                ),
            )
        return self._client

    def upload_file(
        self,
        local_filename: Path,
        remote_filename: Path,
    ) -> str:
        bucket = self.client.lookup_bucket(self.bucket_name)
        blob = bucket.blob(remote_filename.as_posix())
        blob.upload_from_filename(local_filename.as_posix())
        return blob.media_link

    def upload_folder(self, local_directory: Path, remote_directory: Path):
        filenames = glob.glob(local_directory.as_posix() + "/**", recursive=True)
        for filename in map(Path, filenames):
            if os.path.isfile(filename):
                self.upload_file(
                    local_filename=filename,
                    remote_filename=remote_directory.joinpath(
                        filename.relative_to(local_directory)
                    ),
                )
