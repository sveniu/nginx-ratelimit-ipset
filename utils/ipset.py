from io import StringIO


def parse_ipset_list_output(s):
    """
    Example output of `ipset list set1 -terse`:

      Name: set1
      Type: hash:net
      Revision: 6
      Header: family inet hashsize 1024 maxelem 9000 timeout 9001 counters comment
      Size in memory: 1044
      References: 0
      Number of entries: 1
    """
    info = {}

    f = StringIO(s)
    for line in f:
        if line.startswith("Name:"):
            info["name"] = line.split(":")[1].strip()

        elif line.startswith("Type:"):
            info["type"] = line.split(":")[1].strip()

        elif line.startswith("Revision:"):
            info["revision"] = int(line.split(":")[1])

        elif line.startswith("Size in memory:"):
            info["memory_size"] = int(line.split(":")[1])

        elif line.startswith("References:"):
            info["references"] = int(line.split(":")[1])

        elif line.startswith("Number of entries:"):
            info["entry_count"] = int(line.split(":")[1])

        elif line.startswith("Header:"):
            info["header"] = {}
            header = info["header"]
            tokens = line.split(":")[1].split()

            # Old-school loop for old-school parsing.
            i = 0
            while i < len(tokens):
                token = tokens[i]
                if token in ("family", "hashsize", "maxelem", "timeout"):
                    # Key-value-like headers.
                    val = tokens[i + 1]
                    try:
                        # Opportunistic cast to integer.
                        val = int(val)
                    except ValueError:
                        pass
                    header[token] = val

                    # Skip a token, since we already consumed it as a value.
                    i += 1

                elif token in ("counters", "comment"):
                    # Boolean-like headers.
                    header[token] = True

                i += 1

    return info
