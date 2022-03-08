import logging
import os.path
import queue
import sys
import threading
from datetime import datetime

import yaml
from pythonjsonlogger import jsonlogger

from . import ipset, tail

logger = logging.getLogger()

config_file_paths = (
    "./config.yml",
    "~/.config/nginx-limit-ipset/config.yml",
    "/etc/nginx-limit-ipset/config.yml",
)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom formatter for python-json-logger. Lifted straight from
    https://github.com/madzak/python-json-logger#customizing-fields
    """

    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get("timestamp"):
            now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            log_record["timestamp"] = now
        if log_record.get("level"):
            log_record["level"] = log_record["level"].upper()
        else:
            log_record["level"] = record.levelname


def main():
    config = None
    for fn in config_file_paths:
        try:
            with open(os.path.expanduser(fn), "r") as f:
                config = yaml.load(f, yaml.SafeLoader)
                break
        except FileNotFoundError as e:
            logger.warn("config file not found", extra={"path": fn, "exception": e})

    if config is None:
        logger.error(
            "no config file found",
            extra={
                "attempted_paths": config_file_paths,
            },
        )
        raise RuntimeError(
            f"no config file found; tried: {'; '.join(config_file_paths)}"
        )

    # Update log level from config.
    logger.setLevel(config.get("log_level", logging.INFO))

    threads = []
    for lf in config["nginx_log_files"]:
        fn = lf["log_file_path"]
        q = queue.Queue(lf.get("tail_stdout_queue_size", 1000))
        ipset_manager = ipset.IPSetManager(lf["ipset_maps"])

        threads.extend(
            [
                threading.Thread(target=ipset_manager.add_to_ipset, args=(q,)),
                threading.Thread(target=tail.tail_with_retry, args=(fn, q)),
            ]
        )

    # Start all threads.
    [t.start() for t in threads]

    try:
        # Wait for all threads to complete.
        [t.join() for t in threads]
    except KeyboardInterrupt:
        q.put(None)
        [t.join(0.2) for t in threads]
        raise RuntimeError("keyboard interrupt")


def cli():
    logHandler = logging.StreamHandler()
    formatter = CustomJsonFormatter("%(timestamp)s %(name)s %(level)s %(message)s")
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    logger.setLevel(logging.NOTSET)

    try:
        main()
    except Exception as e:
        logger.error("unhandled exception; exiting", extra={"exception": e})
        sys.exit(1)
