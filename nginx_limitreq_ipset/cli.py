import logging
import queue
import sys
import threading
from datetime import datetime

from pythonjsonlogger import jsonlogger

from . import ipset, tail


# https://github.com/madzak/python-json-logger#customizing-fields
class CustomJsonFormatter(jsonlogger.JsonFormatter):
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

    q = queue.Queue(maxsize=100)  # FIXME more? no limit?
    fn = sys.argv[1]

    threads = [
        threading.Thread(target=ipset.add_to_ipset, args=(q,)),
        threading.Thread(target=tail.tail_forever, args=(fn, q)),
    ]
    [t.start() for t in threads]
    [t.join() for t in threads]


def cli():
    main()
