from .cache import SimpleCache
from .helpers import JSON2PY, PY2JSON, INSP_JSON, INSP_PY, PATTERN
from . import pattern

import logging

logger = logging.getLogger(__name__)
TRACE = 5


def trace(fmt, *args, _logger=logger, _TRACE=TRACE):
    "Trace a log message. Avoids issues with applications setting `style`."
    if _logger.isEnabledFor(_TRACE):
        _logger.log(_TRACE, fmt.format(*args))


def set_trace(enabled=True):
    logger.level = TRACE if enabled else logging.WARNING


class SimpleRuleSet:
    """
    This is the base of RuleSet and doesn't know anything about the standard verbs.

    A ruleset contains a series of rules that will be evaluated, in order, against types to attempt to construct
    encoders and decoders.

    It takes a list of rules; functions that accept a verb and type and return actions.

    The keyword argument `cache` can specify a custom rule cache. `json_syntax.cache.ThreadLocalCache` may be helpful
    if you are loading rules in a multi-threaded environment.
    """

    def __init__(self, *rules, cache=None):
        self.rules = rules
        self.cache = cache or SimpleCache()

    def lookup(self, verb, typ, accept_missing=False):
        trace("lookup({!s}, {!r}): start", verb, typ)
        if typ is None:
            if accept_missing:
                trace("lookup({!s}, {!r}): attempt fallabck", verb, typ)
                typ = self.fallback(verb=verb, typ=typ)
            if typ is None:
                raise TypeError("Attempted to find {} for 'None'".format(verb))

        with self.cache.access() as cache:
            action = cache.get(verb=verb, typ=typ)
            if action is not None:
                trace("lookup({!s}, {!r}): cached", verb, typ)
                return action

            forward = cache.in_flight(verb=verb, typ=typ)

            try:
                for rule in self.rules:
                    action = rule(verb=verb, typ=typ, ctx=self)
                    if action is not None:
                        cache.complete(verb=verb, typ=typ, action=action)
                        trace("lookup({!s}, {!r}): computed", verb, typ)
                        return action

                trace("lookup({!s}, {!r}): fallback", verb, typ)
                action = self.fallback(verb=verb, typ=typ)
                if action is not None:
                    cache.complete(verb=verb, typ=typ, action=action)
                    trace("lookup({!s}, {!r}): computed by fallback", verb, typ)
                    return action
            finally:
                cache.de_flight(verb=verb, typ=typ, forward=forward)

        if action is None and not accept_missing:
            raise TypeError("Failed: lookup({!s}, {!r})".format(verb, typ))

    def fallback(self, verb, typ):
        return None


class RuleSet(SimpleRuleSet):
    """
    A ruleset contains a series of rules that will be evaluated, in order, against types to attempt
    to construct encoders and decoders.

    It takes a list of rules; functions that accept a verb and type and return actions.

    The keyword argument `cache` can specify a custom rule cache. `json_syntax.cache.ThreadLocalCache`
    may be helpful if you are loading rules in a multi-threaded environment.

    The most important methods are generally `json_to_python` and `python_to_json`; these take a
    fully specified type and produce an encoder and decoder respectively.
    """

    def json_to_python(self, typ):
        """
        Constructs a function to decode JSON objects (dict, list, str, float, etc.) into
        a Python class for the given type.

        The function will accept a single argument, an object returned by `json.loads`
        or a similar method, and return the Python native instance.
        """
        return self.lookup(verb=JSON2PY, typ=typ)

    def python_to_json(self, typ):
        """
        Constructs a function to encode a Python class into JSON objects (dict, list,
        str, float, etc.) for the given type.

        The function will accept a single argument, a Python instance, and return an
        object that can be passed to `json.dumps` or a similar method.
        """
        return self.lookup(verb=PY2JSON, typ=typ)

    def inspect_json(self, typ):
        """
        Constructs a function that inspects a JSON object (dict, list, str, float, etc.)
        to determine if they match the pattern expected by the given type.

        The function will accept a single argument, an object returned by `json.loads`
        or a similar method, and return True if a call to the decoder function
        constructed by `json_to_python` is expected to succeed.

        Note that some objects that fail this test could nevertheless be converted by
        `json_to_python`.
        """
        return self.lookup(verb=INSP_JSON, typ=typ)

    def inspect_python(self, typ):
        """
        Constructs a function that inspects a value to determine if it matches a given
        type.

        The function will accept a single argument, a standard instance, and return True
        if a call to the encoder function generated by `python_to_json` is expected to
        succeed.

        Note that some objects that fail this test could nevertheless be converted by
        `python_to_json`.
        """
        return self.lookup(verb=INSP_PY, typ=typ)

    def show_pattern(self, typ):
        """
        Analyze a type to determine the structure it will have in its JSON
        representation if `python_to_json` is called against an instance.

        This method does not consider the impact of the `__json_pre_decode__` or
        `__json_post_decode__` hooks.

        It will return a `json_syntax.pattern.Pattern` instance.
        """
        return self.lookup(verb=PATTERN, typ=typ)

    def is_ambiguous(self, typ, threshold=pattern.Matches.always):
        """
        Determine if a type's representation as JSON is ambiguous according to rules
        specified in this ruleset.

        This should only be an issue if you are using `typing.Union` in your data.

        The `threshold` specifies the level below which a pattern is flagged as
        ambiguous.
        """
        pat = self.show_pattern(typ=typ)
        return pattern.is_ambiguous(pat, threshold=threshold)

    def fallback(self, verb, typ):
        """
        Subclasses may override this method to provide fallback handling when the type
        is not provided, or if no action is available for that type.

        *If the type is known but doesn't fit a standard rule, it's best to provide a
         custom rule.*

        A subclass must check the verb and type (which will be None when missing) and
        return a function that performs the task specified by the verb.
        """
        if verb == PATTERN:
            return pattern.Unknown
        else:
            super().fallback(verb, typ)
