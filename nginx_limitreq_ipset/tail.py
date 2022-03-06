import subprocess
import threading

import backoff


def errlog(pipe):
    with pipe:
        for line in iter(pipe.readline, b""):
            print("stderr log:", line.strip())


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
    p = subprocess.Popen(
        ["tail", "-n", "0", "-F", fn],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    threads = [
        threading.Thread(target=reader, args=(p.stdout, q)),
        threading.Thread(target=errlog, args=(p.stderr,)),
    ]
    [t.start() for t in threads]
    [t.join() for t in threads]

    # FIXME log process returncode
    rc = p.wait()
    return rc


def tail_forever(fn, q):
    """
    Tail the specified file using tail(1). Write stdout lines to a queue. Retry
    on failure.
    """
    tail(fn, q)
