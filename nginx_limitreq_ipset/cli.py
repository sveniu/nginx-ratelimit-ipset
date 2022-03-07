import logging
import os.path
import queue
import sys
import threading
from datetime import datetime

import yaml
from pythonjsonlogger import jsonlogger

from . import ipset, tail

config_file_paths = (
    "./config.yml",
    "~/.config/nginx-limitreq-ipset/config.yml",
    "/etc/nginx-limitreq-ipset/config.yml",
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
    logger = logging.getLogger()
    logHandler = logging.StreamHandler()
    formatter = CustomJsonFormatter("%(timestamp)s %(name)s %(level)s %(message)s")
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    logger.setLevel(logging.NOTSET)

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
            "no config found; exiting",
            extra={
                "attempted_paths": config_file_paths,
            },
        )
        sys.exit(1)

    threads = []
    for cfg in config["zone_ipset_maps"]:
        fn = cfg["log_file_path"]
        q = queue.Queue(config.get("tail_stdout_queue_size", 1000))
        ipset_manager = ipset.IPSetManager(cfg)

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
        logger.warn("got keyboard interrupt; exiting")
        q.put(None)
        [t.join(0.2) for t in threads]


def cli():
    main()
