from warnings import warn
import threading


class UnhashableType(UserWarning):
    pass


class ForwardAction:
    """
    A mutable callable. Since actions are simply functions, this lets us create a
    promise of a function and replace it when we have the actual function ready. This is
    a simple way to handle cycles in types.
    """

    __slots__ = ("__call__",)

    def __init__(self, call):
        self.__call__ = call

    def __repr__(self):
        return "<fwd {!r}>".format(self.__call__)


class SimpleCache:
    def __init__(self):
        self.cache = {}

    def get(self, verb, typ):
        result = self._lookup(verb, typ)
        return result if result is not NotImplemented else None

    def _lookup(self, verb, typ):
        """
        Handle unhashable types by warning about them.
        """
        try:
            return self.cache.get((verb, typ))
        except TypeError:
            warn(
                "Type {} is unhashable; json_syntax probably can't handle this".format(
                    typ
                ),
                category=UnhashableType,
            )
            return NotImplemented

    def in_flight(self, verb, typ):
        """
        Called when we begin determining the action for a type. We construct a forward
        action that will be fulfilled by the ``complete`` call.
        """
        if self._lookup(verb, typ) is None:

            def unfulfilled(value):
                # This can't be pickled, which is a good thing.
                raise TypeError(
                    "Forward reference was never fulfilled to {} for {}".format(
                        verb, typ
                    )
                )

            forward = ForwardAction(unfulfilled)
            self.cache[verb, typ] = forward
            return forward

    def de_flight(self, verb, typ, forward):
        """
        If a lookup fails, this removes the entry so that further attempts can be made.
        """
        present = self._lookup(verb, typ)
        if present is forward:
            del self.cache[verb, typ]

    def complete(self, verb, typ, action):
        """
        Once a type is complete, we fulfill any ForwardActions and replace the cache
        entry with the actual action.
        """
        present = self._lookup(verb, typ)
        if present is NotImplemented:
            return  # Unhashable.
        elif present is None:
            self.cache[verb, typ] = action
        elif isinstance(present, ForwardAction):
            present.__call__ = action
            # Replace the cache entry, if it's never been used let the ForwardAction be
            # garbage collected.
            self.cache[verb, typ] = action


class ThreadLocalCache(SimpleCache):
    """
    Avoids threads conflicting while looking up rules by keeping the cache in thread local storage.

    You can also prevent this by looking up rules during module loading.
    """

    def __init__(self):
        self._local = threading.local()

    @property
    def cache(self):
        local = self._local
        try:
            return local.cache
        except AttributeError:
            _cache = local.cache = {}
            return _cache
