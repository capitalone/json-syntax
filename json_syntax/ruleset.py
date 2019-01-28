class NullCache:
    '''
    A stub cache object to describe the API. This will actually work for types without cycles.
    '''
    def get(self, *, verb, typ):
        return None

    def in_flight(self, *, verb, typ):
        pass

    def complete(self, *, verb, typ, converter):
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
            if fallback is None:
                raise TypeError(f"Attempted to find {verb} for 'None' but no fallback defined.")
            return fallback(verb)

        # if not isinstance(typ, type):
        #     raise TypeError(f"Attempted to find {verb} for non-type {typ}.")

        converter = self.cache.get(verb=verb, typ=typ)
        if converter is not None:
            return converter

        self.cache.in_flight(verb=verb, typ=typ)

        for rule in self.rules:
            converter = rule(verb=verb, typ=typ, ctx=self)
            if converter is not None:
                self.cache.complete(verb=verb, typ=typ, converter=converter)
                return converter

        if fallback is None:
            raise TypeError(f"Can't find {verb} to handle {typ} and no fallback defined")

    lookup_inner = lookup
