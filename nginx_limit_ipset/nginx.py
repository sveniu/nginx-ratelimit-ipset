import re
from enum import Enum


class LimitReqRealm(Enum):
    REQUESTS = 1
    CONNECTIONS = 2


class LimitReqAction(Enum):
    LIMIT = 1
    DELAY = 2


class UnhandledEventException(Exception):
    pass


def parse_limit_req(s):
    """
    Parse a line from ngx_http_limit_req_module or ngx_http_limit_conn_module,
    and return a dictionary with the parsed values.
    """

    m = re.match(
        r".*\b(?P<action>limiting|delaying) (?P<realm>requests|connections)\b", s
    )
    if not m:
        raise UnhandledEventException("not a limit_req event")

    realm_str = m.group("realm")
    realm = None
    if realm_str == "requests":
        realm = LimitReqRealm.REQUESTS
    elif realm_str == "delaying":
        realm = LimitReqRealm.CONNECTIONS

    action_str = m.group("action")
    action = None
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
        "realm": realm,
        "action": action,
        "excess": excess,
        "zone": zone,
        "dry_run": dry_run,
        "addr": addr,
    }
