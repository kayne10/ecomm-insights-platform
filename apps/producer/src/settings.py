import logging
import os

from common.settings import KafkaConfig


class ProducerConfig:
    """
    Configuration for confluent-kafka Producer
    """
    BOOTSTRAP_SERVERS = KafkaConfig.BOOTSTRAP_SERVERS

    @classmethod
    def as_dict(cls):
        return {
            "bootstrap.servers": cls.BOOTSTRAP_SERVERS,
        }


def setup_logger(name: str = "producer", level=None) -> logging.Logger:
    """
    Setup and return a logger with consistent formatting.
    Level defaults to the LOG_LEVEL env var (INFO if unset).
    """
    level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger(name)
    if not logger.handlers:  # Prevent duplicate handlers if re-imported
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
