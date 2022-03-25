# Nginx rate-limited client address to Linux IP sets

Get offender IPs from Nginx limit_conn or limit_req logs and insert them into
Linux netfilter IP sets for further iptables processing.

Offload high-volume connection- or request-based (D)DoS attacks to iptables,
instead of letting Nginx spend CPU cycles on them, especially if TLS is
involved.

## Overview

Create an IP set of type `hash:net` with: a one-hour default timeout; forced add
with random eviction; counters and comment support.

```sh
sudo ipset create offenders hash:net timeout 3600 forceadd counters comment
```

Add an iptables rule that drops packets originating from IP addresses in the
offenders IP set.

```sh
sudo iptables -A INPUT -p tcp --dport 80 -m set --match-set offenders src -j DROP
```

Configure Nginx with error logging and two simple rate limits.

```nginx
events {}
http {
 error_log /var/log/nginx/error.log error;
 limit_req_zone $binary_remote_addr zone=req_zone:10m rate=10r/s;
 limit_conn_zone $binary_remote_addr zone=conn_zone:10m;

 server {
    listen 80;
    root /var/www/html;
    location / {
        limit_req zone=req_zone burst=50 nodelay;
        limit_conn conn_zone 20;
        try_files $uri $uri/ =404;
    }
  }
}
```

Put the following configuration into `config.yml`:

```yaml
---
sources:
  - type: NGINX_RATELIMIT
    config:
      error_log_file_path: /var/log/nginx/error.log
      ratelimit_zone_name: req_zone

    sinks:
      - type: LINUX_IPSET
        config:
          ipset_name: offenders

  - type: NGINX_RATELIMIT
    config:
      error_log_file_path: /var/log/nginx/error.log
      ratelimit_zone_name: conn_zone
      ratelimit_type: CONNECTIONS

    sinks:
      - type: LINUX_IPSET
        config:
          ipset_name: offenders
```

Run the program with `nginx-ratelimit-ipset config.yml` and it will log activity
to stderr. Observe IP addresses being immediately added to the IP set, right as
they are logged by Nginx.

## Configuration

The configuration is a single YAML file, searched at these locations:

- The first argument on the command line

- `./config.yml`

- `~/.config/nginx-limit-ipset/config.yml`

- `/etc/nginx-limit-ipset/config.yml`

See examples/config.yml for a full example configuration with documentation.

The general structure of the configuration file is a list of zero or more
sources, each with a list of zero or more sinks.

```yaml
---
sources:
  - type: SOME_SOURCE
    config:
      config_param1: val1
      config_param2: val2

    sinks:
      - type: SOME_SINK
        config:
          config_param1: val1
          config_param2: val2

      - type: OTHER_SINK
        config:
          config_param1: val1
          config_param2: val2

  - type: OTHER_SOURCE
    config:
      config_param1: val1
      config_param2: val2

    sinks:
      - type: SOME_SINK
        config:
          config_param1: val1
          config_param2: val2
```

Global configuration parameters:

`log_level` (default: INFO): Control the log level. Set to `DEBUG` when
troubleshooting.

## Sources and sinks

A couple of sources and sinks are available.

### Source: `NGINX_RATELIMIT`

Read the Nginx error log and extract entries coming from the limit_req or
limit_conn modules.

Example:

```yaml
---
sources:
  - type: NGINX_RATELIMIT
    config:
      error_log_file_path: /var/log/nginx/error.log
      ratelimit_zone_name: req_zone
```

Configuration options:

`error_log_file_path` (no default): Absolute or relative path to the Nginx error
log file.

`ratelimit_zone_name` (no default): Name of the Nginx shared memory zone,
corresponding to the Nginx limit_req or limit_conn zone name.

`ratelimit_type` (default: REQUESTS): This can either be REQUESTS (Nginx
ngx_http_limit_req_module) or CONNECTIONS (Nginx ngx_http_limit_conn_module).

`ratelimit_action` (default: LIMIT): This can either be LIMIT or DELAY,
corresponding to Nginx limiting or delaying events.

`ratelimit_ignore_if_dry_run` (default: true): Control whether to ignore events
that are marked as dry run by the Nginx limit_{req,conn}_dry_run directives.

`ignore_cidrs` (default: `127.0.0.0/8`, `::1`): If an event's address or CIDR is
partly or wholly contained within any of the listed CIDRs, the event is ignored
and will not be propagated to sinks. Values can be bare IPv4/IPv6 addresses, or
IPv4/IPv6 CIDRs.

`cache_size` (default: 10000): The number of addresses that can be cached, for
de-duplication purposes. When full, items are discarded in LRU order. A value of
0 disables caching.

`cache_ttl_seconds` (default: 60.0): The number of seconds to keep addresses in
the cache before they expire.

Compatibility: Works with any Nginx version starting with 0.7.25 (ca 2008),
which added logging of the limit_req zone name.

### Sink: `LINUX_IPSET`

Add entries to a Linux netfilter IP set.

Example:

```yaml
---
    sinks
    - type: LINUX_IPSET
      config:
        ipset_name: offenders
```

`ipset_name` (no default): Name of the IP set to add entries to. The IP set must
already exist.

`dry_run` (default: false): If enabled, entries are logged; no entries are added
to the IP set.

`entry_default_timeout_seconds` (default: 3600): Default timout for entries.

`entry_default_comment` (default: dynamic): Set a static comment for entries
inserted into the IP set. By default, the comment contains an `added_at`
timestamp.

`ignore_cidrs` (default: `127.0.0.0/8`, `::1`): If an event's address or CIDR is
partly or wholly contained within any of the listed CIDRs, the event is ignored
and will not be propagated to sinks. Values can be bare IPv4/IPv6 addresses, or
IPv4/IPv6 CIDRs.

`cache_size` (default: 10000): The number of addresses that can be cached, for
de-duplication purposes. When full, items are discarded in LRU order. A value of
0 disables caching.

`cache_ttl_seconds` (default: 60.0): The number of seconds to keep addresses in
the cache before they expire.
