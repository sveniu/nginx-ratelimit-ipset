import re
from enum import Enum


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
