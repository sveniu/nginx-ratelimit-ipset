# Nginx rate-limited client address to netfilter IP sets

Get offender IPs from Nginx limit_conn or limit_req logs and insert them into
netfilter IP sets for further iptables processing.

Offload high-volume connection- or request-based (D)DoS attacks to iptables,
instead of letting Nginx spend CPU cycles on them, especially if TLS is
involved.

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

Configure Nginx with error logging and two simple rate limits.

```nginx
events {}
http {
 error_log /var/log/nginx/error.log error;
 limit_req_zone $binary_remote_addr zone=req_zone:10m rate=10r/s;
 limit_conn_zone $binary_remote_addr zone=conn_zone:10m;

 server {
    listen 80;
    location / {
        limit_req zone=req_zone burst=50 nodelay;
        limit_conn conn_zone 20;
        return 200 "Hello, World!";
    }
  }
}
```

Put the following configuration into `/etc/nginx-ratelimit-ipset/config.yml`:

```yaml
---
FIXME: restructure for multiple things from a single file
zone_ipset_maps:
  - log_file_path: /var/log/nginx/error.log
    ratelimit_zone_name: myzone
    ipset_name: offenders
```

Run the program with `nginx-ratelimit-ipset` and it will log activity to stderr.
Observe IP addresses being immediately added to the IP set, just as they are
logged by Nginx.

## Details

TBD.

Type: connections, requests
Action: limit, delay
Excess: .. ignored
Dry run.

## Configuration

TDB.

## Compatibility

Works with any Nginx version starting with 0.7.25 (ca 2008), which added logging
of the limit_req zone name.
