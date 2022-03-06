import logging

logger = logging.getLogger(__name__)


def add_to_ipset(q):
    for item in iter(q.get, None):
        logger.info("got item", extra={"item": item})
