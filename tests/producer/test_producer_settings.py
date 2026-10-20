import logging


def test_logger_level_comes_from_log_level(app_module, monkeypatch):
    settings = app_module("producer", "settings")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    logger = settings.setup_logger("test-producer-debug")

    assert logger.level == logging.DEBUG


def test_logger_is_not_duplicated_when_set_up_twice(app_module):
    settings = app_module("producer", "settings")

    logger = settings.setup_logger("test-producer-once")
    settings.setup_logger("test-producer-once")

    assert len(logger.handlers) == 1
