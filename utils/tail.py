import logging
import threading
from enum import Enum

from . import execute

logger = logging.getLogger(__name__)


class StdStreamType(Enum):
    STDOUT = 1
    STDERR = 2


def reader(pipe, qstdio):
    """
    Read lines from the given pipe (io.BufferedReader). Handle lines according
    to the stream type (stdout vs stderr).
    """

    with pipe:
        for line in iter(pipe.readline, b""):
            qstdio.put(line)


def tail(fn, qstdout, qstderr):
    """
    Tail the specified file using tail(1). Write stdout lines to a queue.

    Execute the system tail(1); don't output any lines on startup; follow files
    through renames.

    FIXME make this a utility func
    """

    argv = ["tail", "-n", "0", "-F", fn]
    p = execute.popen(argv)

    logger.debug("tail process started", extra={"file_path": fn, "argv": argv})

    threads = [
        threading.Thread(target=reader, args=(p.stdout, qstdout)),
        threading.Thread(target=reader, args=(p.stderr, qstderr)),
    ]
    [t.start() for t in threads]
    [t.join() for t in threads]

    # Wait for process to exit.
    r = p.wait()

    # FIXME Close the queues?
    return r
