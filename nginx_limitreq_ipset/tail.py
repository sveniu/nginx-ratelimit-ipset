import logging
import re
import subprocess
import threading
from enum import Enum

import backoff

logger = logging.getLogger(__name__)


class StdStreamType(Enum):
    STDOUT = 1
    STDERR = 2


class LimitReqAction(Enum):
    LIMIT = 1
    DELAY = 2


class UnhandledEventException(Exception):
    pass


def parse_limit_req(s):
    m = re.match(r".*\b(?P<action>limiting|delaying) requests\b", s)
    if not m:
        raise UnhandledEventException("not a limit_req event")

    action_str = m.group("action")
    if action_str == "limiting":
        action = LimitReqAction.LIMIT
    elif action_str == "delaying":
        action = LimitReqAction.DELAY

    m = re.match(r".*\bexcess: (?P<excess>[\d.]+)", s)
    if not m:
        raise UnhandledEventException("excess not parsed")

    excess = m.group("excess")

    m = re.match(r'.*\bzone "(?P<zone>[^"]+)"', s)
    if not m:
        raise UnhandledEventException("zone not parsed")

    zone = m.group("zone")

    dry_run = False
    m = re.match(r".*\bdry run\b", s)  # nginx 1.17.1 and later
    if m:
        dry_run = True

    m = re.match(r".*\bclient: (?P<addr>[^,]+),", s)
    if not m:
        raise UnhandledEventException("client addr not parsed")

    addr = m.group("addr")

    return {
        "action": action,
        "excess": excess,
        "zone": zone,
        "dry_run": dry_run,
        "addr": addr,
    }


def reader(pipe, stream_type, q=None):
    with pipe:
        for line in iter(pipe.readline, b""):
            s = line.decode("utf-8").strip()

            if stream_type is StdStreamType.STDOUT:
                try:
                    q.put(parse_limit_req(s))
                except UnhandledEventException as e:
                    logger.debug("unhandled event", extra={"exception": e})

            if stream_type is StdStreamType.STDERR:
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
