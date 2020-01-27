class _Context:
    """
    Stash contextual information in an exception. As we don't know exactly when an exception
    is displayed to a user, this class tries to keep it always up to date.

    This class subclasses string (to be compatible) and tracks an insertion point.
    """

    __slots__ = ("original", "context", "lead")

    def __init__(self, original, lead, context):
        self.original = original
        self.lead = lead
        self.context = [context]

    def __str__(self):
        return "{}{}{}".format(
            self.original, self.lead, "".join(map(str, reversed(self.context)))
        )

    def __repr__(self):
        return repr(self.__str__())

    @classmethod
    def add(cls, exc, context):
        args = exc.args
        if args and isinstance(args[0], cls):
            args[0].context.append(context)
            return
        args = list(exc.args)
        if args:
            args[0] = cls(args[0], "; at ", context)
        else:
            args.append(cls("", "At ", context))
        exc.args = tuple(args)


class ErrorContext:
    """
    Inject contextual information into an exception message. This won't work for some
    exceptions like OSError that ignore changes to `args`; likely not an issue for this
    library. There is a neglible performance hit if there is no exception.

    >>> with ErrorContext('.foo'):
    ...   with ErrorContext('[0]'):
    ...     with ErrorContext('.qux'):
    ...       1 / 0
    Traceback (most recent call last):
    ZeroDivisionError: division by zero; at .foo[0].qux

    The `__exit__` method will catch the exception and look for a `_context` attribute
    assigned to it. If none exists, it appends `; at ` and the context string to the first
    string argument.

    As the exception walks up the stack, outer ErrorContexts will be called. They will see
    the `_context` attribute and insert their context immediately after `; at ` and before
    the existing context.

    Thus, in the example above:

        ('division by zero',)  -- the original message
        ('division by zero; at .qux',)  -- the innermost context
        ('division by zero; at [0].qux',)
        ('division by zero; at .foo[0].qux',) -- the outermost context

    For simplicity, the method doesn't attempt to inject whitespace. To represent names,
    consider surrounding them with angle brackets, e.g. `<Class>`
    """

    def __init__(self, *context):
        self.context = context

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is not None:
            _Context.add(exc_value, "".join(self.context))


def err_ctx(context, func):
    """
    Execute a callable, decorating exceptions raised with error context.

    ``err_ctx(context, func)`` has the same effect as:

        with ErrorContext(context):
            return func()
    """
    try:
        return func()
    except Exception as exc:
        _Context.add(exc, context)
        raise
