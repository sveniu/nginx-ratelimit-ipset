import logging
import signal
import subprocess
import threading
import time
from enum import Enum

from . import nginx

logger = logging.getLogger(__name__)


class StdStreamType(Enum):
    STDOUT = 1
    STDERR = 2


def reader(pipe, stream_type, q=None):
    """
    Read lines from the given pipe (io.BufferedReader). Handle lines according
    to the stream type (stdout vs stderr).
    """

    with pipe:
        for line in iter(pipe.readline, b""):
            s = line.decode("utf-8").strip()

            if stream_type is StdStreamType.STDOUT:
                try:
                    q.put(nginx.parse_limit_req(s))
                except nginx.UnhandledEventException as e:
                    logger.debug("unhandled event", extra={"exception": e})

            if stream_type is StdStreamType.STDERR:
                logger.info("read from stderr", extra={"stderr": s})


def tail(fn, q):
    """
    Tail the specified file using tail(1). Write stdout lines to a queue.

    Execute the system tail(1); don't output any lines on startup; follow files
    through renames.
    """

    cmd = ["/usr/bin/tail", "-n", "0", "-F", fn]
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    logger.info("tail process started", extra={"file_path": fn, "argv": cmd})

    threads = [
        threading.Thread(target=reader, args=(p.stdout, StdStreamType.STDOUT, q)),
        threading.Thread(target=reader, args=(p.stderr, StdStreamType.STDERR)),
    ]
    [t.start() for t in threads]
    [t.join() for t in threads]

    return p.wait()


def tail_with_retry(fn, q):
    """
    Tail the specified file using tail(1). Write stdout lines to a queue. Retry
    on failure.
    """
    while True:
        rc = tail(fn, q)
        if rc == -1 * signal.SIGINT:
            break

        logger.warn("unexpected subprocess exit", extra={"returncode": rc})
        time.sleep(2.0)
