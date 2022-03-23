import logging

from utils import exec

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

        exec.execute(cmd)
        logger.info(
            "ipset entry added successfully",
            extra={
                "item": item,
                "argv": cmd,
            },
        )


# Raise exception early if list command fails.
# FIXME actually don't. only raise if plugin is actually used
exec.execute([LinuxIPSetSink.ipset_cmd, "list"])
