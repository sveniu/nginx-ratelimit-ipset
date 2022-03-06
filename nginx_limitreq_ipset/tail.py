import subprocess
import threading


def errlog(pipe):
    with pipe:
        for line in iter(pipe.readline, b""):
            print("stderr log:", line.strip())


def reader(pipe, q):
    """
    https://stackoverflow.com/a/31867499/3555015
    """
    try:
        with pipe:
            for line in iter(pipe.readline, b""):
                q.put(line)
    finally:
        q.put(None)


def tail_forever(fn, q):
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

    p.wait()  # FIXME check returncode, raise if non-zero
