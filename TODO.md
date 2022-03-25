# TODO

IPSet class.

Generic tail plugin, and NGINX_RATELIMIT sink inherits from it?

Figure out how to do testing, especially wrt plugins.

Read Nginx error log from journald.

Double check all log event levels.

Add sink: Redis.

Add source: Redis.

Monitor ipset statistics and increase the ttl on entries that still receive
traffic; but only up to a certain max duration.

Send metrics to statsd?

Encode more info into the ipset entry's comment field.

Establish what an "item" (aka event) is, data structure wise. Currently it's
decided by utils.nginx:parse_ratelimit_line. This also plays into how the
de-duplication caching would work, as that one only looks at the addr field, for
the time being.
