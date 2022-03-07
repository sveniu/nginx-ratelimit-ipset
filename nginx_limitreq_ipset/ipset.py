import logging
import subprocess

logger = logging.getLogger(__name__)


ipset_cmd = "/usr/sbin/ipset"
ipset_set = "autoban"
ipset_timeout = "121"
ipset_comment = "my-test-comment"


def add_to_ipset(q):
    for item in iter(q.get, None):
        logger.debug("got item", extra={"item": item})

        cmd = [
            ipset_cmd,
            "-exist",
            "add",
            ipset_set,
            item["addr"],
            "timeout",
            ipset_timeout,
            "comment",
            ipset_comment,
        ]

        try:
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            logger.error(
                "error starting subprocess",
                extra={
                    "argv": cmd,
                    "exception": e,
                },
            )
            continue

        try:
            stdout, stderr = p.communicate(timeout=2.0)
        except subprocess.TimeoutExpired:
            p.kill()
            stdout, stderr = p.communicate()

        if p.returncode != 0:
            logger.error(
                "subprocess failed",
                extra={
                    "argv": cmd,
                    "rc": p.returncode,
                    "stdout": stdout.decode("utf-8").strip(),
                    "stderr": stderr.decode("utf-8").strip(),
                },
            )
