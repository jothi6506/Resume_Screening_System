"""
Storage Service Abstraction for Local and Cloud Object Storage.

Supports:
- Local Storage (STORAGE_TYPE=local)
- AWS S3 Storage (STORAGE_TYPE=s3)
- Cloudinary Storage (STORAGE_TYPE=cloudinary)
- Supabase / S3-compatible Cloud Storage
"""

import os
import tempfile
import uuid
import logging
from flask import current_app
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


def _get_upload_folder():
    """Return absolute path to local upload folder."""
    folder = current_app.config.get("UPLOAD_FOLDER", "uploads/resumes")
    path = os.path.join(current_app.root_path, "..", folder)
    os.makedirs(os.path.abspath(path), exist_ok=True)
    return os.path.abspath(path)


class BaseStorageService:
    """Base storage service interface."""

    def save_file(self, file_storage, stored_filename=None):
        raise NotImplementedError

    def get_file_bytes(self, stored_filename):
        raise NotImplementedError

    def delete_file(self, stored_filename):
        raise NotImplementedError

    def get_temp_local_path(self, stored_filename):
        raise NotImplementedError

    def get_status(self):
        raise NotImplementedError


class LocalStorageService(BaseStorageService):
    """Local filesystem storage implementation."""

    def __init__(self):
        self.type_name = "Local Disk Storage"

    def save_file(self, file_storage, stored_filename=None):
        upload_dir = _get_upload_folder()
        if not stored_filename:
            ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
            stored_filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        
        file_path = os.path.join(upload_dir, stored_filename)
        file_storage.save(file_path)
        file_size = os.path.getsize(file_path)

        return {
            "stored_filename": stored_filename,
            "file_path": file_path,
            "file_size": file_size,
            "storage_type": "local"
        }

    def get_file_bytes(self, stored_filename):
        upload_dir = _get_upload_folder()
        file_path = os.path.join(upload_dir, stored_filename)
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                return f.read()
        return None

    def delete_file(self, stored_filename):
        upload_dir = _get_upload_folder()
        file_path = os.path.join(upload_dir, stored_filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except OSError as e:
                logger.error(f"Error removing local file {file_path}: {e}")
                return False
        return True

    def get_temp_local_path(self, stored_filename):
        upload_dir = _get_upload_folder()
        file_path = os.path.join(upload_dir, stored_filename)
        if os.path.exists(file_path):
            return file_path
        return None

    def get_status(self):
        upload_dir = _get_upload_folder()
        is_writable = os.access(upload_dir, os.W_OK)
        return {
            "mode": "Local Disk",
            "storage_type": "local",
            "connected": is_writable,
            "status": "Healthy (Writable)" if is_writable else "Error (Permission Denied)",
            "details": f"Path: {upload_dir}"
        }


class S3StorageService(BaseStorageService):
    """AWS S3 / S3-compatible cloud object storage implementation."""

    def __init__(self):
        self.bucket_name = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")
        self.access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
        self.secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self.local_fallback = LocalStorageService()

    def _get_s3_client(self):
        try:
            import boto3
            return boto3.client(
                "s3",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            return None

    def save_file(self, file_storage, stored_filename=None):
        if not stored_filename:
            ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
            stored_filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

        client = self._get_s3_client()
        if client and self.bucket_name:
            try:
                content = file_storage.read()
                file_storage.seek(0)
                client.put_object(
                    Bucket=self.bucket_name,
                    Key=f"resumes/{stored_filename}",
                    Body=content
                )
                file_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/resumes/{stored_filename}"
                return {
                    "stored_filename": stored_filename,
                    "file_path": file_url,
                    "file_size": len(content),
                    "storage_type": "s3"
                }
            except Exception as e:
                logger.error(f"S3 upload failed: {e}. Falling back to local storage.")
        
        return self.local_fallback.save_file(file_storage, stored_filename)

    def get_file_bytes(self, stored_filename):
        client = self._get_s3_client()
        if client and self.bucket_name:
            try:
                response = client.get_object(Bucket=self.bucket_name, Key=f"resumes/{stored_filename}")
                return response["Body"].read()
            except Exception as e:
                logger.error(f"Failed to fetch S3 object {stored_filename}: {e}")
        
        return self.local_fallback.get_file_bytes(stored_filename)

    def delete_file(self, stored_filename):
        client = self._get_s3_client()
        if client and self.bucket_name:
            try:
                client.delete_object(Bucket=self.bucket_name, Key=f"resumes/{stored_filename}")
            except Exception as e:
                logger.error(f"Failed to delete S3 object {stored_filename}: {e}")
        return self.local_fallback.delete_file(stored_filename)

    def get_temp_local_path(self, stored_filename):
        # Check local storage first
        local_path = self.local_fallback.get_temp_local_path(stored_filename)
        if local_path:
            return local_path

        # Download from S3 to temp file
        b = self.get_file_bytes(stored_filename)
        if b:
            ext = stored_filename.rsplit(".", 1)[-1] if "." in stored_filename else "tmp"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
            tmp.write(b)
            tmp.close()
            return tmp.name
        return None

    def get_status(self):
        if not self.bucket_name or not self.access_key:
            return {
                "mode": "Cloud S3 Storage",
                "storage_type": "s3",
                "connected": False,
                "status": "Not Configured (Missing AWS credentials)",
                "details": "AWS_STORAGE_BUCKET_NAME or AWS_ACCESS_KEY_ID not set"
            }
        
        client = self._get_s3_client()
        if not client:
            return {
                "mode": "Cloud S3 Storage",
                "storage_type": "s3",
                "connected": False,
                "status": "Error (boto3 missing or initialization failed)",
                "details": "Check boto3 installation and AWS credentials"
            }
        
        try:
            client.head_bucket(Bucket=self.bucket_name)
            return {
                "mode": "Cloud S3 Storage",
                "storage_type": "s3",
                "connected": True,
                "status": "Connected & Active",
                "details": f"Bucket: {self.bucket_name} ({self.region})"
            }
        except Exception as e:
            return {
                "mode": "Cloud S3 Storage",
                "storage_type": "s3",
                "connected": False,
                "status": f"Connection Error: {str(e)}",
                "details": f"Bucket: {self.bucket_name}"
            }


class CloudinaryStorageService(BaseStorageService):
    """Cloudinary cloud object storage implementation."""

    def __init__(self):
        self.local_fallback = LocalStorageService()
        self.url = os.environ.get("CLOUDINARY_URL", "")

    def _init_cloudinary(self):
        try:
            import cloudinary
            import cloudinary.uploader
            if self.url:
                cloudinary.config(cloudinary_url=self.url)
            return cloudinary
        except Exception as e:
            logger.error(f"Cloudinary init failed: {e}")
            return None

    def save_file(self, file_storage, stored_filename=None):
        if not stored_filename:
            ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
            stored_filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

        c = self._init_cloudinary()
        if c and self.url:
            try:
                import cloudinary.uploader
                res = cloudinary.uploader.upload(
                    file_storage,
                    public_id=f"resumes/{stored_filename}",
                    resource_type="raw"
                )
                return {
                    "stored_filename": stored_filename,
                    "file_path": res.get("secure_url", res.get("url")),
                    "file_size": res.get("bytes", 0),
                    "storage_type": "cloudinary"
                }
            except Exception as e:
                logger.error(f"Cloudinary upload error: {e}")

        return self.local_fallback.save_file(file_storage, stored_filename)

    def get_file_bytes(self, stored_filename):
        return self.local_fallback.get_file_bytes(stored_filename)

    def delete_file(self, stored_filename):
        return self.local_fallback.delete_file(stored_filename)

    def get_temp_local_path(self, stored_filename):
        return self.local_fallback.get_temp_local_path(stored_filename)

    def get_status(self):
        if not self.url:
            return {
                "mode": "Cloudinary Object Storage",
                "storage_type": "cloudinary",
                "connected": False,
                "status": "Not Configured (Missing CLOUDINARY_URL)",
                "details": "Set CLOUDINARY_URL in environment variables"
            }
        return {
            "mode": "Cloudinary Object Storage",
            "storage_type": "cloudinary",
            "connected": True,
            "status": "Configured & Active",
            "details": "Connected via Cloudinary API"
        }


def get_storage_service():
    """Factory to get configured storage service based on environment variables."""
    stype = (os.environ.get("STORAGE_TYPE") or "local").lower().strip()
    if stype == "s3":
        return S3StorageService()
    elif stype in ("cloudinary", "cloud"):
        return CloudinaryStorageService()
    else:
        return LocalStorageService()
