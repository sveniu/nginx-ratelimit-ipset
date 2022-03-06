def add_to_ipset(q):
    for item in iter(q.get, None):
        print("add_to_ipset got item:", item)
