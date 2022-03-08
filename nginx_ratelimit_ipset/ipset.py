import logging

from . import exec, nginx

logger = logging.getLogger(__name__)


class IPSetManager:
    ipset_cmd = "/usr/sbin/ipset"

    def __init__(self, mappings):
        self.mappings = mappings

    def get_mapping_matching_item(self, item):
        """
        Find a mapping with matching type, action and zone name.
        """

        for mapping in self.mappings:
            rltype = nginx.LimitType[mapping["ratelimit_type"]]
            if not item["type"] is rltype:
                logger.debug(
                    "limit_req type mismatch",
                    extra={
                        "wanted": rltype,
                        "got": item["type"],
                    },
                )
                continue

            action = nginx.LimitAction[mapping["ratelimit_action"]]
            if not item["action"] is action:
                logger.debug(
                    "limit_req action mismatch",
                    extra={
                        "wanted": action,
                        "got": item["action"],
                    },
                )
                continue

            zone_name = mapping["ratelimit_zone_name"]
            if not item["zone"] == zone_name:
                logger.debug(
                    "limit_req zone mismatch",
                    extra={
                        "wanted": zone_name,
                        "got": item["zone"],
                    },
                )
                continue

            # All checks passed; return mapping.
            yield mapping

    def add_to_ipset(self, q):
        """
        Fetch items (parsed ngx_http_limit_{req,conn}_module events) from the
        given queue. Use ipset to add the items to an IP set.
        """

        for item in iter(q.get, None):
            logger.debug("got item", extra={"item": item})

            for mapping in self.get_mapping_matching_item(item):
                # Check whether to add entry, even if logged as "dry run" by nginx.
                if item["dry_run"] and not mapping["ratelimit_add_dry_run"]:
                    logger.debug("dry run; no action")
                    continue

                cmd = [
                    IPSetManager.ipset_cmd,
                    "-exist",
                    "add",
                    mapping["ipset_name"],
                    item["addr"],
                ]

                if "ipset_entry_timeout_seconds" in mapping:
                    cmd.extend(
                        [
                            "timeout",
                            str(mapping["ipset_entry_timeout_seconds"]),
                        ]
                    )

                if "ipset_entry_comment" in mapping:
                    cmd.extend(
                        [
                            "comment",
                            mapping["ipset_entry_comment"],
                        ]
                    )

                if mapping.get("ipset_dry_run", False):
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
