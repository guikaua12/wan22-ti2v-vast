import boto3
from pathlib import Path


class R2Storage:
    def __init__(self, config):
        self.bucket = config.s3_bucket_name
        self.client = boto3.client(
            "s3",
            endpoint_url=config.s3_endpoint_url,
            aws_access_key_id=config.s3_access_key_id,
            aws_secret_access_key=config.s3_secret_access_key,
            region_name=config.s3_region,
        )

    def upload(self, path: Path, storage_key: str, media_type: str) -> dict:
        self.client.upload_file(
            str(path),
            self.bucket,
            storage_key,
            ExtraArgs={"ContentType": media_type},
        )
        return {
            "storageKey": storage_key,
            "mediaType": media_type,
            "sizeBytes": path.stat().st_size,
        }
