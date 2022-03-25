from collections.abc import MutableMapping


class nulldict(MutableMapping, dict):
    """
    A /dev/null-like dict that never stores keys.
    """

    def __setitem__(self, key, value):
        pass
