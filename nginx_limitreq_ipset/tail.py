import logging
import subprocess
import threading
from enum import Enum

import backoff

logger = logging.getLogger(__name__)


class StdStreamType(Enum):
    STDOUT = 1
    STDERR = 2


def reader(pipe, stds, q=None):
    with pipe:
        for line in iter(pipe.readline, b""):
            s = line.decode("utf-8").strip()

            if stds is StdStreamType.STDOUT:
                if q is not None:
                    q.put(s)

            if stds is StdStreamType.STDERR:
                logger.info("read from stderr", extra={"stderr": s})


# Retry this function indefinitely by always returning True for the predicate.
# This will restart the tail process if it fails for any reason, using an
# expotential backoff with a maximum interval.
@backoff.on_predicate(backoff.expo, lambda x: True, max_time=30.0)
def tail(fn, q):
    """
    Tail the specified file using tail(1). Write stdout lines to a queue.
    """
    cmd = ["/usr/bin/tail", "-n", "0", "-F", fn]
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    logger.info("now tailing file", extra={"argv": cmd})

    threads = [
        threading.Thread(target=reader, args=(p.stdout, StdStreamType.STDOUT, q)),
        threading.Thread(target=reader, args=(p.stderr, StdStreamType.STDERR)),
    ]
    [t.start() for t in threads]
    [t.join() for t in threads]

    rc = p.wait()
    logger.warn("unexpected subprocess exit", extra={"command": cmd, "returncode": rc})
    return rc


def tail_forever(fn, q):
    """
    Tail the specified file using tail(1). Write stdout lines to a queue. Retry
    on failure.
    """
    tail(fn, q)
