import logging

from . import exec, nginx

logger = logging.getLogger(__name__)


class IPSetManager:
    ipset_cmd = "/usr/sbin/ipset"

    def __init__(self, config):
        self.config = config

    def add_to_ipset(self, q):
        """
        Fetch items (parsed ngx_http_limit_{req,conn}_module events) from the
        given queue. Use ipset to add the items to an IP set.
        """

        for item in iter(q.get, None):
            logger.debug("got item", extra={"item": item})

            # Check whether to add entry, even if logged as "dry run" by nginx.
            if item["dry_run"] and not self.config["ratelimit_add_dry_run"]:
                logger.debug("dry run; no action")
                continue

            rltype = nginx.LimitType[self.config["ratelimit_type"]]
            if not item["type"] is rltype:
                logger.debug(
                    "limit_req type mismatch",
                    extra={
                        "wanted": rltype,
                        "got": item["type"],
                    },
                )
                continue

            action = nginx.LimitAction[self.config["ratelimit_action"]]
            if not item["action"] is action:
                logger.debug(
                    "limit_req action mismatch",
                    extra={
                        "wanted": action,
                        "got": item["action"],
                    },
                )
                continue

            zone_name = self.config["ratelimit_zone_name"]
            if not item["zone"] == zone_name:
                logger.debug(
                    "limit_req zone mismatch",
                    extra={
                        "wanted": zone_name,
                        "got": item["zone"],
                    },
                )
                continue

            cmd = [
                IPSetManager.ipset_cmd,
                "-exist",
                "add",
                self.config["ipset_name"],
                item["addr"],
            ]

            if "ipset_entry_timeout_seconds" in self.config:
                cmd.extend(
                    [
                        "timeout",
                        str(self.config["ipset_entry_timeout_seconds"]),
                    ]
                )

            if "ipset_entry_comment" in self.config:
                cmd.extend(
                    [
                        "comment",
                        self.config["ipset_entry_comment"],
                    ]
                )

            if self.config.get("ipset_dry_run", False):
                logger.info(
                    "dry run; would have added entry",
                    extra={
                        "item": item,
                        "argv": cmd,
                    },
                )
                continue

            try:
                exec.execute(cmd)
                logger.info(
                    "ipset entry added successfully",
                    extra={
                        "item": item,
                        "argv": cmd,
                    },
                )
            except exec.NonZeroExitException:
                pass


# Raise exception early if list command fails.
exec.execute([IPSetManager.ipset_cmd, "list"])
