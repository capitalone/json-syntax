from warnings import warn


class UnhashableType(UserWarning):
    pass


class ForwardConverter:
    '''
    A mutable callable. Since converters are simply functions, this lets us create a promise of a function and replace
    it when we have the actual function ready. This is a simple way to handle cycles in types.
    '''
    __slots__ = ('__call__',)

    def __init__(self, call):
        self.__call__ = call

    @property
    def __name__(self):
        return f'forward_to_{self.__call__.__name__}'



class SimpleCache:
    def __init__(self, warn_unhashable=True):
        self.cache = {}

    def get(self, *, verb, typ):
        result = self._lookup(verb, typ)
        return result if result is not NotImplemented else None

    def _lookup(self, verb, typ):
        '''
        Handle unhashable types by warning about them.
        '''
        try:
            return self.cache.get((verb, typ), None)
        except TypeError:
            if warn_unhashable:
                warn(f"Type {typ} is unhashable; json_syntax probably can't handle this", category=UnhashableType)
            return NotImplemented

    def in_flight(self, *, verb, typ):
        '''
        Called when we begin determining the converter for a type. We construct a forward converter that will be fulfilled
        by the ``complete`` call.
        '''
        if self._lookup(verb, typ) is None:
            def unfulfilled(value):
                # This can't be pickled, which is a good thing.
                raise TypeError(f"Forward reference was never fulfilled to {verb} for {typ}")

            self.cache[(verb, typ)] = ForwardConverter(unfulfilled)

    def complete(self, *, verb, typ, converter):
        '''
        Once a type is complete, we fulfill any ForwardConverters and replace the cache entry with the actual converter.
        '''
        present = self._lookup(verb, typ)
        if present is NotImplemented:
            return  # Unhashable.
        elif present is None:
            self.cache[(verb, typ)] = converter
        elif isinstance(present, ForwardConverter):
            present.__call__ = converter
            # Replace the cache entry, if it's never been used let the ForwardConverter be garbage collected.
            self.cache[(verb, typ)] = converter
