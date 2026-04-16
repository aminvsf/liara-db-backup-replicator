import os.path

import boto3
import requests
from botocore.exceptions import ClientError
from requests import RequestException

from src.config import config
from src.domains import Backup
from src.liara.exceptions import LiaraAPIError
from src.utilities.encryption import EncryptedFileObj
from src.utilities.logger import logger


class S3Storage:

    def __init__(self, database, bucket):
        self.database = database
        self.bucket = bucket

        self.client = self._get_client()

        self._existing_backups = None

    def _get_client(self):
        kwargs = {
            "aws_access_key_id": self.bucket.access_key,
            "aws_secret_access_key": self.bucket.secret_key,
        }
        if self.bucket.region:
            kwargs["region_name"] = self.bucket.region
        if self.bucket.endpoint_url:
            kwargs["endpoint_url"] = str(self.bucket.endpoint_url)

        return boto3.client("s3", **kwargs)

    def _get_extra_prefix(self):
        extra_prefix = self.bucket.prefix or config.s3.default_prefix
        if not extra_prefix:
            return ""
        return "%s/" % extra_prefix.strip("/\\")

    def _get_existing_backups(self):
        if self._existing_backups:
            return self._existing_backups

        existing_backups = []
        prefix = self._get_extra_prefix() + f"{self.database.name}/"
        for page in self.client.get_paginator("list_objects_v2").paginate(
            Bucket=self.bucket.name, Prefix=prefix
        ):
            for obj in page.get("Contents", ()):
                if obj["Key"] != prefix:
                    existing_backups.append(
                        Backup.from_s3_obj(self.database, prefix, obj)
                    )
        self._existing_backups = existing_backups
        return existing_backups

    def _get_backup_key(self, backup):
        key = os.path.join(self._get_extra_prefix(), self.database.name, backup.name)
        if config.s3.encryption.enabled:
            key += ".enc"
        return key

    def _upload_backup(self, backup):
        logger.info(
            "Uploading backup '%s' of database '%s'...", backup.name, self.database.name
        )

        try:
            backup_download_url = backup.get_download_url()
        except LiaraAPIError as exc:
            logger.error(
                "Failed to fetch backup download URL from the Liara API: %s",
                exc.message,
            )
            return False

        try:
            response = requests.get(backup_download_url, stream=True, timeout=60)
            response.raise_for_status()
        except RequestException as exc:
            logger.error("Failed to download backup from Liara: %s", exc)
            return False

        if config.s3.encryption.enabled:
            content_iterator = response.iter_content(chunk_size=1024 * 1024 * 25)
            file_obj = EncryptedFileObj(
                content_iterator, key=config.s3.encryption.secret_key
            )
        else:
            file_obj = response.raw

        try:
            self.client.upload_fileobj(
                file_obj, self.bucket.name, self._get_backup_key(backup)
            )
        except ClientError as exc:
            logger.error("Failed to upload backup to '%s': %s", self.bucket.title, exc)
            return False
        finally:
            response.close()
        return True

    def _delete_old_backups(self, current_backups):
        logger.info("Deleting old backups of '%s'...", self.bucket.title)

        existing_backups = self._get_existing_backups()
        old_backups = set(existing_backups) - set(current_backups)
        if old_backups:
            logger.info(
                "Found %d old backup(s) to delete. Deleting...", len(old_backups)
            )
        else:
            logger.info("No old backups to delete.")
            return

        try:
            response = self.client.delete_objects(
                Bucket=self.bucket.name,
                Delete={
                    "Objects": [
                        {"Key": self._get_backup_key(b) for b in old_backups},
                    ],
                    "Quiet": False,
                },
            )
        except ClientError as exc:
            logger.error(
                "Failed to delete old backups of '%s': %s", self.bucket.title, exc
            )
            return

        if "Errors" in response:
            logger.error(
                "Failed to delete old backups of '%s': %s",
                self.bucket.title,
                "\n".join(
                    "%s: %s" % (r["Key"], r["Message"]) for r in response["Errors"]
                ),
            )

    def sync_backups(self, backups):
        try:
            existing_backups = self._get_existing_backups()
        except ClientError as exc:
            logger.error(
                "Failed to fetch existing backups from '%s': %s", self.bucket.title, exc
            )
            return

        new_backups = set(backups) - set(existing_backups)
        if new_backups:
            logger.info("Found %d new backup(s) to upload.", len(new_backups))
        else:
            logger.info("No new backups to upload. Bucket is already up-to-date.")
            return

        upload_error_happened = False
        for backup in new_backups:
            uploaded = self._upload_backup(backup)
            if not uploaded:
                upload_error_happened = True

        if upload_error_happened:
            logger.warning(
                "Backup upload process ended with error(s). Refusing to delete "
                "old backups."
            )
            return

        self._delete_old_backups(backups)


class Replicator:

    def __init__(self, database):
        self.database = database

    def run(self):
        logger.info("Replicating database '%s' backups...", self.database.name)

        try:
            backups = self.database.get_backups()
        except LiaraAPIError as exc:
            logger.error("Failed to fetch backups from the Liara API: %s", exc.message)
            return

        for bucket in config.s3.buckets:
            S3Storage(self.database, bucket).sync_backups(backups)
