# Nginx limit_req client address to netfilter IP sets

Get offender IPs from Nginx limit_req logs and insert them into netfilter IP
sets for further iptables processing.

Offload high-volume connection- or request-based

## Overview

Create an IP set of type `hash:ip` with: a one-hour default timeout; forced add
with random eviction; counters and comment support.

```sh
sudo ipset create offenders hash:ip timeout 3600 forceadd counters comment
```

Add an iptables rules that drops packets from IPs in the offenders set.

```sh
sudo iptables -A INPUT -m set --match-set offenders src -j DROP
```

Configure Nginx with error logging and a simple rate limit.

```nginx
http {
    error_log /var/log/nginx/error.log error;

    limit_req_zone $binary_remote_addr zone=myzone:10m rate=1r/s;

    server {
        location /search/ {
            limit_req zone=myzone burst=5;
        }
        …
    }
    …
}
```

Put the following configuration into `/etc/nginx-limitreq-ipset/config.yml`:

```yaml
---
zone_ipset_maps:
  - log_file_path: /var/log/nginx/error.log
    limit_req_zone_name: myzone
    ipset_name: offenders
```

Run the program with `nginx-limitreq-ipset` and it will log activity to stderr.
Observe IP addresses being immediately added to the IP set, just as they are
logged by Nginx.

## Details

TBD.

Realm: connections, requests
Action: limit, delay
Excess: .. ignored
Dry run.

## Configuration

TDB.

## Compatibility

Works with any Nginx version starting with 0.7.25 (ca 2008), which added logging
of the limit_req zone name.
