import queue
import sys
import threading

from . import ipset, tail


def main():
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
