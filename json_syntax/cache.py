from warnings import warn


class UnhashableType(UserWarning):
    pass


class ForwardAction:
    """
    A mutable callable. Since actions are simply functions, this lets us create a promise of a function and replace
    it when we have the actual function ready. This is a simple way to handle cycles in types.
    """

    __slots__ = ("__call__",)

    def __init__(self, call):
        self.__call__ = call

    def __getattr__(self, name):
        if name in ("__name__", "__doc__", "__qualname__"):
            return getattr(self.__call__, name)
        raise AttributeError()

    def __repr__(self):
        return f"<fwd {self.__call__!r}>"


class SimpleCache:
    def __init__(self, warn_unhashable=True):
        self.cache = {}
        self.warn_unhashable = warn_unhashable

    def get(self, *, verb, typ):
        result = self._lookup(verb, typ)
        return result if result is not NotImplemented else None

    def _lookup(self, verb, typ):
        """
        Handle unhashable types by warning about them.
        """
        try:
            return self.cache.get((verb, typ), None)
        except TypeError:
            if self.warn_unhashable:
                warn(f"Type {typ} is unhashable; json_syntax probably can't handle this", category=UnhashableType)
            return NotImplemented

    def in_flight(self, *, verb, typ):
        """
        Called when we begin determining the action for a type. We construct a forward action that will be
        fulfilled by the ``complete`` call.
        """
        if self._lookup(verb, typ) is None:

            def unfulfilled(value):
                # This can't be pickled, which is a good thing.
                raise TypeError(f"Forward reference was never fulfilled to {verb} for {typ}")

            self.cache[(verb, typ)] = ForwardAction(unfulfilled)

    def complete(self, *, verb, typ, action):
        """
        Once a type is complete, we fulfill any ForwardActions and replace the cache entry with the actual action.
        """
        present = self._lookup(verb, typ)
        if present is NotImplemented:
            return  # Unhashable.
        elif present is None:
            self.cache[(verb, typ)] = action
        elif isinstance(present, ForwardAction):
            present.__call__ = action
            # Replace the cache entry, if it's never been used let the ForwardAction be garbage collected.
            self.cache[(verb, typ)] = action
