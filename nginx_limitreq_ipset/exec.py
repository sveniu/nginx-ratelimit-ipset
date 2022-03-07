import logging
import subprocess

logger = logging.getLogger(__name__)


class NonZeroExitException(Exception):
    pass


def execute(cmd, timeout=2.0):
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
        raise

    try:
        stdout, stderr = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        stdout, stderr = p.communicate()

    if p.returncode != 0:
        logger.error(
            "subprocess returned non-zero exit code",
            extra={
                "argv": cmd,
                "rc": p.returncode,
                "stdout": stdout.decode("utf-8").strip(),
                "stderr": stderr.decode("utf-8").strip(),
            },
        )
        raise NonZeroExitException(f"return code: {p.returncode}")
