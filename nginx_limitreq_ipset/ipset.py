import logging

from . import exec, nginx

logger = logging.getLogger(__name__)


class IPSetManager:
    ipset_cmd = "/usr/sbin/ipset"

    def __init__(self, config):
        self.config = config

    def add_to_ipset(self, q):
        """
        Fetch items (parsed ngx_http_limit_req_module events) from the given queue.
        Use ipset to add the items to an IP set.
        """

        for item in iter(q.get, None):
            logger.debug("got item", extra={"item": item})

            # Check whether to add entry, even if logged as "dry run" by nginx.
            if item["dry_run"] and not self.config["limit_req_add_dry_run"]:
                logger.debug("limit_req dry run; no action")
                continue

            action = nginx.LimitReqAction[self.config["limit_req_action"]]
            if not item["action"] is action:
                logger.debug(
                    "limit_req action mismatch",
                    extra={
                        "wanted": action,
                        "got": item["action"],
                    },
                )
                continue

            zone_name = self.config["limit_req_zone_name"]
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

            if "ipset_entry_timeout" in self.config:
                cmd.extend(
                    [
                        "timeout",
                        self.config["ipset_entry_timeout_seconds"],
                    ]
                )

            if "ipset_entry_comment" in self.config:
                cmd.extend(
                    [
                        "comment",
                        self.config["ipset_entry_comment"],
                    ]
                )

            try:
                exec.execute(cmd)
            except exec.NonZeroExitException:
                pass


# Raise exception early if list command fails.
exec.execute([IPSetManager.ipset_cmd, "list"])
