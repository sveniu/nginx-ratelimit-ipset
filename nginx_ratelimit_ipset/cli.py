import logging
import os.path
import queue
import sys
import threading
import traceback

import yaml

from .log import CustomJsonFormatter
from .plugins import plugin_factory

logger = logging.getLogger()

config_file_paths = [
    "./config.yml",
    "~/.config/nginx-limit-ipset/config.yml",
    "/etc/nginx-limit-ipset/config.yml",
]


def main():
    # If supplied, treat the first argument as the configuration file.
    if len(sys.argv) > 1:
        config_file_paths.insert(0, sys.argv[1])

    config = None
    for fn in config_file_paths:
        try:
            with open(os.path.expanduser(fn), "r") as f:
                config = yaml.safe_load(f)
                break
        except FileNotFoundError as e:
            logger.warn("config file not found", extra={"path": fn, "exception": e})

    if config is None:
        logger.error(
            "no config file found",
            extra={
                "attempted_paths": config_file_paths,
            },
        )
        raise RuntimeError(
            f"no config file found; tried: {'; '.join(config_file_paths)}"
        )

    # Update log level from config.
    logger.setLevel(config.get("log_level", logging.INFO))

    # Threads running the process() function of each source/sink.
    process_threads = []

    # List of all queues, for shutdown purposes.
    all_queues = []

    # Iterate over all sources found in the configuration.
    for source_spec in config["sources"]:
        sink_queues = []

        # Iterate over all sinks for this source.
        for sink_spec in source_spec.get("sinks", []):
            sink_queue = queue.Queue(1000)  # FIXME configurable?

            # Instantiate the sink plugin and provide the sink configuration.
            sink = plugin_factory(sink_spec["type"])
            sink.configure(sink_spec["config"])
            sink_queues.append(sink_queue)
            all_queues.append(sink_queue)

            # Prepare the sink's process() thread and provide the sink queue.
            process_threads.append(
                threading.Thread(target=sink.process, args=(sink_queue,))
            )

        # Instantiate the source plugin and provide the source configuration.
        source = plugin_factory(source_spec["type"])
        source.configure(source_spec["config"])

        # Prepare the source process() and provide the sink queues.
        process_threads.append(
            threading.Thread(target=source.process, args=(sink_queues,))
        )

    # Start all process() threads.
    [t.start() for t in process_threads]

    try:
        # Wait for all process() threads to complete.
        [t.join() for t in process_threads]
    except KeyboardInterrupt:
        [q.put(None) for q in all_queues]
        [t.join(0.2) for t in process_threads]
        raise RuntimeError("keyboard interrupt")


def cli():
    logHandler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter("%(timestamp)s %(name)s %(level)s %(message)s")
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    logger.setLevel(logging.NOTSET)

    try:
        main()
    except Exception as e:
        logger.error(
            "unhandled exception; exiting",
            extra={"exception": e, "traceback": traceback.format_exc()},
        )
        sys.exit(1)
