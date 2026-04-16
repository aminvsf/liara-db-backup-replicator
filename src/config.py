import sys
import tomllib
from pathlib import Path
from tomllib import TOMLDecodeError
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, ValidationError, model_validator

from src.utilities.logger import logger

BASE_DIR = Path(__file__).resolve().parent.parent


class LiaraConfig(BaseModel):
    api_token: str
    team_id: Optional[str] = None
    api_url: Optional[HttpUrl] = None
    target_databases: Optional[List[str]] = None


class BucketConfig(BaseModel):
    name: str
    access_key: str
    secret_key: str
    region: Optional[str] = None
    endpoint_url: Optional[HttpUrl] = None
    alias: Optional[str] = None
    prefix: Optional[str] = None

    @property
    def title(self):
        return self.alias or self.name


class EncryptionConfig(BaseModel):
    enabled: bool = False
    secret_key: Optional[str] = None

    @model_validator(mode="after")
    def clean_secret_key(self):
        if self.enabled:
            if self.secret_key:
                try:
                    self.secret_key = bytes.fromhex(self.secret_key)
                except ValueError:
                    raise ValueError(
                        "The provided secret_key is not a valid hexadecimal string. "
                        "You can generate a secure 32-byte hex key by running "
                        "the following command in your terminal:\n"
                        'python -c "import secrets; print(secrets.token_hex(32))"\n'
                    )
            else:
                raise ValueError("secret_key is required when encryption is enabled")
        return self


class S3Config(BaseModel):
    default_prefix: Optional[str] = None
    buckets: List[BucketConfig]
    encryption: EncryptionConfig = EncryptionConfig()


class AppConfig(BaseModel):
    liara: LiaraConfig
    s3: S3Config


CONFIG_PATH = BASE_DIR / "config.toml"

config = None
try:
    with open(CONFIG_PATH, "rb") as file:
        data = tomllib.load(file)
    config = AppConfig(**data)

except FileNotFoundError:
    logger.error(
        "The 'config.toml' file was not found. Please ensure you have created "
        "this file and it is in the root directory of the project. You can use "
        "'config.example.toml' as a starting point."
    )
except TOMLDecodeError as exc:
    logger.error("The 'config.toml' file contains invalid TOML syntax: %s", exc)
except ValidationError as exc:
    logger.error("The 'config.toml' file contains invalid data: %s", exc)

if config is None:
    sys.exit(1)
