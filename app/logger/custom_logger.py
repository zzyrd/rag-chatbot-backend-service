"""Main logger module"""
import sys
import json
from loguru import logger

def serialize(record):
    """cutom JSON formatter"""
    subset = {
        "timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S"),
        "message": record["message"],
        "level": record["level"].name,
        "file": record["file"].name,
        "context": record["extra"],
    }
    return json.dumps(subset)

def patching(record):
    """patcher function to customize json format"""
    record["extra"]["serialized"] = serialize(record)

logger = logger.patch(patching)
logger.remove() # remove the default handler configuration
logger.add(sys.stderr, level="WARNING", format="{extra[serialized]}")
logger.add(sys.stdout, level="DEBUG", format="{extra[serialized]}", \
           filter=lambda record: record["level"].no < 30)

# export
log = logger
