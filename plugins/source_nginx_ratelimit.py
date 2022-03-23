import logging
import signal
import subprocess
import threading
import time
from enum import Enum

from utils import nginx

from plugins import BasePlugin, PluginType

logger = logging.getLogger(__name__)


class StdStreamType(Enum):
    STDOUT = 1
    STDERR = 2


class NginxRatelimitSource(BasePlugin):
    plugin_type = PluginType["SOURCE"]
    plugin_name = "NGINX_RATELIMIT"

    def configure(self, config):
        self.config = config

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

        return True

    def reader(self, pipe, stream_type, qs=[]):
        """
        Read lines from the given pipe (io.BufferedReader). Handle lines according
        to the stream type (stdout vs stderr).
        """

        with pipe:
            for line in iter(pipe.readline, b""):
                s = line.decode("utf-8").strip()

                if stream_type is StdStreamType.STDOUT:
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

                    # Put event into all sink queues.
                    for q in qs:
                        q.put(rlevent)

                if stream_type is StdStreamType.STDERR:
                    logger.info("read from stderr", extra={"stderr": s})

    def tail(self, fn, qs):
        """
        Tail the specified file using tail(1). Write stdout lines to a queue.

        Execute the system tail(1); don't output any lines on startup; follow files
        through renames.

        FIXME make this a utility func
        """

        cmd = ["tail", "-n", "0", "-F", fn]
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        logger.info("tail process started", extra={"file_path": fn, "argv": cmd})

        threads = [
            threading.Thread(
                target=self.reader, args=(p.stdout, StdStreamType.STDOUT, qs)
            ),
            threading.Thread(target=self.reader, args=(p.stderr, StdStreamType.STDERR)),
        ]
        [t.start() for t in threads]
        [t.join() for t in threads]

        return p.wait()

    def tail_with_retry(self):
        """
        Tail the specified file using tail(1). Write stdout lines to a queue. Retry
        on failure.
        """
        while True:
            rc = self.tail(self.config["error_log_file_path"], self.qs)
            if rc == -1 * signal.SIGINT:
                break

            logger.warn("unexpected subprocess exit", extra={"returncode": rc})
            time.sleep(2.0)

    def process(self, qs):
        self.qs = qs
        self.tail_with_retry()
