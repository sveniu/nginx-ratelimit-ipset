import logging
import queue
import signal
import threading
import time
from enum import Enum
from ipaddress import ip_network

import cachetools
from nginx_ratelimit_ipset.plugins import BasePlugin, PluginType
from nginx_ratelimit_ipset.utils import nginx, tail, types

logger = logging.getLogger(__name__)


class StdStreamType(Enum):
    STDOUT = 1
    STDERR = 2


class NginxRatelimitSource(BasePlugin):
    plugin_type = PluginType["SOURCE"]
    plugin_name = "NGINX_RATELIMIT"

    def configure(self, config):
        self.config = config

        cache_size = self.config.get("cache_size", 10_000)
        if cache_size > 0:
            self.cache = cachetools.TTLCache(
                self.config.get("cache_size", 10_000),
                self.config.get("cache_ttl_seconds", 60.0),
            )
        else:
            self.cache = types.nulldict()

    def event_matches_config(self, rlevent):
        if (
            not rlevent["type"]
            is nginx.LimitType[self.config.get("ratelimit_type", "REQUESTS")]
        ):
            return False

        if (
            not rlevent["action"]
            is nginx.LimitAction[self.config.get("ratelimit_action", "LIMIT")]
        ):
            return False

        if not rlevent["zone"] == self.config["ratelimit_zone_name"]:
            return False

        if rlevent["dry_run"] and self.config["ratelimit_ignore_if_dry_run"]:
            return False

        addr = ip_network(rlevent["addr"], strict=False)
        for cidrstr in self.config.get("ignore_cidrs", ["127.0.0.0/8", "::1"]):
            cidr = ip_network(cidrstr, strict=False)
            if addr.overlaps(cidr):
                logger.debug(
                    "address matches ignored cidr",
                    extra={
                        "address": addr,
                        "matching_ignore_cidr": cidr,
                    },
                )
                return False

        return True

    def qstdout_handler(self, q, qs):
        for line in iter(q.get, None):
            s = line.decode("utf-8").strip()

            try:
                rlevent = nginx.parse_ratelimit_line(s)
            except nginx.UnhandledEventException as e:
                logger.debug("unhandled event", extra={"exception": e})
                continue

            if not self.event_matches_config(rlevent):
                logger.debug(
                    "event does not match config",
                    extra={"event": rlevent, "config": self.config},
                )
                continue

            if rlevent["addr"] not in self.cache:
                # Put event into all sink queues.
                for q in qs:
                    q.put(rlevent)
                self.cache[rlevent["addr"]] = rlevent
            else:
                logger.debug(
                    "event found in cache; ignoring",
                    extra={"event": rlevent},
                )

    def qstderr_handler(self, q):
        for line in iter(q.get, None):
            s = line.decode("utf-8").strip()
            logger.info("read from stderr", extra={"stderr": s})

    def tail_with_retry(self):
        """
        Tail the specified file using tail(1). Write stdout lines to a queue. Retry
        on failure.
        """
        while True:
            qstdout = queue.Queue(1000)
            qstderr = queue.Queue(1000)

            threads = [
                threading.Thread(target=self.qstdout_handler, args=(qstdout, self.qs)),
                threading.Thread(target=self.qstderr_handler, args=(qstderr,)),
            ]
            [t.start() for t in threads]

            rc = tail.tail(self.config["error_log_file_path"], qstdout, qstderr)

            # Close the queues.
            qstdout.put(None)
            qstderr.put(None)

            [t.join() for t in threads]

            if rc == -1 * signal.SIGINT:
                break

            logger.warn("unexpected subprocess exit", extra={"returncode": rc})
            time.sleep(2.0)

    def process(self, qs):
        self.qs = qs
        self.tail_with_retry()
