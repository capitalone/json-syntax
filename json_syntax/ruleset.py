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
    def __init__(self, *rules, cache=NullCache.instance):
        self.rules = rules
        self.cache = cache

    def lookup(self, *, verb, typ, accept_missing=False):
        if typ is None:
            if not accept_missing:
                raise TypeError(f"Attempted to find {verb} for 'None'")
            return self.fallback(verb=verb, typ=typ)

        action = self.cache.get(verb=verb, typ=typ)
        if action is not None:
            return action

        self.cache.in_flight(verb=verb, typ=typ)

        for rule in self.rules:
            action = rule(verb=verb, typ=typ, ctx=self)
            if action is not None:
                self.cache.complete(verb=verb, typ=typ, action=action)
                return action

        return self.fallback(verb=verb, typ=typ)

    def fallback(self, *, verb, typ):
        raise TypeError(
            f"Attempted to find {verb} for {typ!r} but no fallback defined."
        )
