import logging
import subprocess
import threading

import backoff

logger = logging.getLogger(__name__)


def errlog(pipe):
    with pipe:
        for line in iter(pipe.readline, b""):
            logger.info("got stderr", extra={"stderr": line})


def reader(pipe, q):
    with pipe:
        for line in iter(pipe.readline, b""):
            q.put(line)


# Retry this function indefinitely by always returning True for the predicate.
# This will restart the tail process if it fails for any reason, using an
# expotential backoff with a maximum interval.
@backoff.on_predicate(backoff.expo, lambda x: True, max_time=30.0)
def tail(fn, q):
    """
    Tail the specified file using tail(1). Write stdout lines to a queue.
    """
    cmd = ["tail", "-n", "0", "-F", fn]
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    threads = [
        threading.Thread(target=reader, args=(p.stdout, q)),
        threading.Thread(target=errlog, args=(p.stderr,)),
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
