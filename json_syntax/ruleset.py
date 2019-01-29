class NullCache:
    """
    A stub cache object to describe the API. This will actually work for types without
    cycles.
    """

    def get(self, *, verb, typ):
        return None

    def in_flight(self, *, verb, typ):
        pass

    def complete(self, *, verb, typ, action):
        pass


NullCache.instance = NullCache()


class RuleSet:
    def __init__(self, *rules, cache=NullCache.instance, fallback=None):
        self.rules = rules
        self.cache = cache
        self.fallback = fallback

    def lookup(self, *, verb, typ, accept_missing=False):
        if typ is None:
            if not accept_missing:
                raise TypeError(f"Attempted to find {verb} for 'None'")
            if self.fallback is None:
                raise TypeError(
                    f"Attempted to find {verb} for 'None' but no fallback defined."
                )
            return self.fallback(verb)

        action = self.cache.get(verb=verb, typ=typ)
        if action is not None:
            return action

        self.cache.in_flight(verb=verb, typ=typ)

        for rule in self.rules:
            action = rule(verb=verb, typ=typ, ctx=self)
            if action is not None:
                self.cache.complete(verb=verb, typ=typ, action=action)
                return action

        if self.fallback is None:
            raise TypeError(
                f"Can't find {verb} to handle {typ} and no fallback defined"
            )

    lookup_inner = lookup
