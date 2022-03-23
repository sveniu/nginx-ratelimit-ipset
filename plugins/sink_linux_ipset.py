import datetime
import logging
from ipaddress import ip_network

from utils import execute, ipset

from plugins import BasePlugin, PluginType

logger = logging.getLogger(__name__)


class LinuxIPSetSink(BasePlugin):
    plugin_type = PluginType["SINK"]
    plugin_name = "LINUX_IPSET"
    ipset_cmd = "ipset"

    def configure(self, config):
        self.config = config
        self.detect_ipset_ip_version()

    def process(self, q):
        for item in iter(q.get, None):
            logger.debug("got item", extra={"item": item})

            try:
                self.handle_item(item)
            except Exception as e:
                logger.error("error", extra={"error": e})

    def detect_ipset_ip_version(self):
        # Auto-detect the IP set address family.
        stdout, _ = execute.simple(
            [
                LinuxIPSetSink.ipset_cmd,
                "list",
                self.config["ipset_name"],
                "-terse",
            ]
        )
        ipset_list_info = ipset.parse_ipset_list_output(stdout)
        logger.debug("got ipset info", extra={"ipset": ipset_list_info})

        # Map the IP set family "inet" to 4 and "inet6" to 6.
        self.ipset_ip_version = {"inet": 4, "inet6": 6}[
            ipset_list_info["header"]["family"]
        ]

    def handle_item(self, item):
        # Parse the item address as an IP address.
        addr = ip_network(item["addr"], strict=False)

        # Verify IP version match.
        if not addr.version == self.ipset_ip_version:
            logger.debug(
                "ip version mismatch",
                extra={
                    "address": addr,
                    "got_ip_version": addr.version,
                    "ipset_ip_version": self.ipset_ip_version,
                },
            )
            return

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
                return

        cmd = [
            LinuxIPSetSink.ipset_cmd,
            "-exist",
            "add",
            self.config["ipset_name"],
            item["addr"],
        ]

        cfgkey = "entry_default_timeout_seconds"
        if cfgkey in self.config:
            cmd.extend(
                [
                    "timeout",
                    str(self.config[cfgkey]),
                ]
            )

        cfgkey = "entry_default_comment"
        if cfgkey in self.config:
            comment = self.config[cfgkey]
        else:
            data = {
                "added_at": (
                    datetime.datetime.utcnow()
                    .replace(tzinfo=datetime.timezone.utc)
                    .isoformat()
                )
            }

            # Format: key1=val1; key2=val2; ...
            comment = "; ".join([f"{k}={v}" for k, v in data.items()])

        cmd.extend(["comment", comment])

        if self.config.get("dry_run", False):
            logger.info(
                "dry run; would have added ipset entry",
                extra={
                    "item": item,
                    "argv": cmd,
                },
            )
            return

        execute.simple(cmd)
        logger.info(
            "ipset entry added successfully",
            extra={
                "item": item,
                "argv": cmd,
            },
        )


# Raise exception early if list command fails.
# FIXME actually don't. only raise if plugin is actually used
execute.simple([LinuxIPSetSink.ipset_cmd, "list"])
