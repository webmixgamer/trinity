"""
S3-compatible storage for log archives.

Supports AWS S3, MinIO, Cloudflare R2, and other S3-compatible services.
"""
import os
import logging
from typing import Optional, Dict
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logging.warning("boto3 not available - S3 uploads will be disabled")

logger = logging.getLogger(__name__)


class S3ArchiveStorage:
    """S3-compatible storage handler for log archives."""

    def __init__(
        self,
        bucket: str,
        access_key: str,
        secret_key: str,
        endpoint: Optional[str] = None,
        region: str = "us-east-1",
    ):
        """
        Initialize S3 storage.

        Args:
            bucket: S3 bucket name
            access_key: AWS access key or compatible
            secret_key: AWS secret key or compatible
            endpoint: Custom endpoint URL (for MinIO, R2, etc.)
            region: AWS region (default: us-east-1)
        """
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for S3 uploads. Install with: pip install boto3")

        if not bucket or not access_key or not secret_key:
            raise ValueError("S3 bucket, access_key, and secret_key are required")

        self.bucket = bucket
        self.endpoint = endpoint
        self.region = region

        # Initialize S3 client
        config_args = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
        }

        if endpoint:
            config_args["endpoint_url"] = endpoint

        self.client = boto3.client("s3", **config_args)

        # Verify bucket access
        self._verify_bucket()

    def _verify_bucket(self):
        """Verify that the bucket exists and is accessible."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"S3 bucket verified: {self.bucket}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                raise ValueError(f"S3 bucket does not exist: {self.bucket}")
            elif error_code == "403":
                raise ValueError(f"Access denied to S3 bucket: {self.bucket}")
            else:
                raise ValueError(f"Failed to access S3 bucket: {e}")
        except NoCredentialsError:
            raise ValueError("Invalid S3 credentials")

    async def upload_file(
        self,
        file_path: str,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload a file to S3.

        Args:
            file_path: Local file path
            s3_key: S3 object key (path in bucket)
            metadata: Optional metadata dict

        Returns:
            S3 URL of uploaded file

        Raises:
            Exception if upload fails
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            extra_args = {
                "ServerSideEncryption": "AES256",  # Encrypt at rest
            }

            if metadata:
                extra_args["Metadata"] = metadata

            # Upload file
            self.client.upload_file(
                Filename=str(file_path_obj),
                Bucket=self.bucket,
                Key=s3_key,
                ExtraArgs=extra_args,
            )

            # Construct S3 URL
            if self.endpoint:
                s3_url = f"{self.endpoint}/{self.bucket}/{s3_key}"
            else:
                s3_url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{s3_key}"

            logger.info(f"Uploaded {file_path_obj.name} to S3: {s3_key}")
            return s3_url

        except ClientError as e:
            error_msg = f"S3 upload failed for {s3_key}: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def delete_file(self, s3_key: str):
        """
        Delete a file from S3.

        Args:
            s3_key: S3 object key to delete
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"Deleted from S3: {s3_key}")
        except ClientError as e:
            logger.error(f"Failed to delete {s3_key} from S3: {e}")
            raise

    def list_files(self, prefix: str = "") -> list:
        """
        List files in S3 bucket with optional prefix.

        Args:
            prefix: Key prefix to filter by

        Returns:
            List of S3 object keys
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
            )

            if "Contents" not in response:
                return []

            return [obj["Key"] for obj in response["Contents"]]

        except ClientError as e:
            logger.error(f"Failed to list S3 objects: {e}")
            raise

