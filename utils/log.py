import logging
import os
import datetime
from colorlog import ColoredFormatter
from logging.handlers import TimedRotatingFileHandler

FORMAT_FILE = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
FORMATTER_CONSOLE = "%(log_color)s%(asctime)s - %(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(name)s:%(lineno)d | %(log_color) s%(message)s%(reset)s"

LOG_FILE = datetime.datetime.now().strftime("%Y_%m_%d") + "_" + str(os.path.basename(__file__).replace(".py", ".txt"))


def setup_console_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = ColoredFormatter(FORMATTER_CONSOLE)

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    return logger


def get_file_handler(log_file):
    file_handler = TimedRotatingFileHandler(log_file, when='midnight')
    file_handler.setFormatter(FORMAT_FILE)
    return file_handler


if __name__ == '__main__':
    logger = setup_console_logger("root")
    logger.debug("a debug message")
    logger.info("Curious users might want to know this")
    logger.error("Serious stuff, this is red for a reason")
    logger.critical("OH NO everything is on fire")
