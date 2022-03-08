import re
from enum import Enum


class LimitType(Enum):
    REQUESTS = 1
    CONNECTIONS = 2


class LimitAction(Enum):
    LIMIT = 1
    DELAY = 2


class UnhandledEventException(Exception):
    pass


def parse_ratelimit_line(s):
    """
    Parse a line from ngx_http_limit_{req,conn}_module and return a dictionary
    with the parsed values.
    """

    m = re.match(
        r".*\b(?P<action>limiting|delaying) (?P<type>requests|connections)\b", s
    )
    if not m:
        raise UnhandledEventException("not a ratelimit log line")

    rltype = None
    rltype_str = m.group("type")
    if rltype_str == "requests":
        rltype = LimitType.REQUESTS
    elif rltype_str == "connections":
        rltype = LimitType.CONNECTIONS

    action = None
    action_str = m.group("action")
    if action_str == "limiting":
        action = LimitAction.LIMIT
    elif action_str == "delaying":
        action = LimitAction.DELAY

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
        "type": rltype,
        "action": action,
        "excess": excess,
        "zone": zone,
        "dry_run": dry_run,
        "addr": addr,
    }
