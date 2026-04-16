import logging
import os

logger = logging.getLogger()

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
)
