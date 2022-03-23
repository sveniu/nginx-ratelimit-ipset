import logging
from ipaddress import ip_network

from utils import execute

from plugins import BasePlugin, PluginType

logger = logging.getLogger(__name__)


class LinuxIPSetSink(BasePlugin):
    plugin_type = PluginType["SINK"]
    plugin_name = "LINUX_IPSET"
    ipset_cmd = "ipset"

    def configure(self, config):
        self.config = config

    def process(self, q):
        for item in iter(q.get, None):
            logger.debug("got item", extra={"item": item})

            try:
                self.handle_item(item)
            except Exception as e:
                logger.error("error", extra={"error": e})

    def handle_item(self, item):
        # Parse the item address as an IP address.
        addr = ip_network(item["addr"], strict=False)

        # Verify IP version match.
        expected_ip_version = self.config.get("ip_version", 4)

        if not addr.version == expected_ip_version:
            logger.debug(
                "ip version mismatch",
                extra={
                    "address": addr,
                    "got_version": addr.version,
                    "expected_version": expected_ip_version,
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
            cmd.extend(
                [
                    "comment",
                    self.config[cfgkey],
                ]
            )

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
