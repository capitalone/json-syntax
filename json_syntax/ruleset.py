from .cache import SimpleCache
from .helpers import PATTERN
from . import pattern

import logging

logger = logging.getLogger(__name__)
TRACE = 5


def trace(fmt, *args, _logger=logger, _TRACE=TRACE):
    "Trace a log message. Avoids issues with applications setting `style`."
    if _logger.isEnabledFor(_TRACE):
        _logger.log(_TRACE, fmt.format(args))


def set_trace(enabled=True):
    logger.level = TRACE if enabled else logging.WARNING


class RuleSet:
    def __init__(self, *rules, cache=None):
        self.rules = rules
        self.cache = cache or SimpleCache()

    def lookup(self, verb, typ, accept_missing=False):
        trace("lookup({!s}, {!r}): start", verb, typ)
        if typ is None:
            if not accept_missing:
                raise TypeError("Attempted to find {} for 'None'".format(verb))
            return self.fallback(verb=verb, typ=typ)

        action = self.cache.get(verb=verb, typ=typ)
        if action is not None:
            trace("lookup({!s}, {!r}): cached", verb, typ)
            return action

        forward = self.cache.in_flight(verb=verb, typ=typ)

        try:
            for rule in self.rules:
                action = rule(verb=verb, typ=typ, ctx=self)
                if action is not None:
                    self.cache.complete(verb=verb, typ=typ, action=action)
                    trace("lookup({!s}, {!r}): computed", verb, typ)
                    return action

            trace("lookup({!s}, {!r}): fallback", verb, typ)
            action = self.fallback(verb=verb, typ=typ)
            if action is not None:
                self.cache.complete(verb=verb, typ=typ, action=action)
                trace("lookup({!s}, {!r}): computed by fallback", verb, typ)
                return action
        finally:
            self.cache.de_flight(verb=verb, typ=typ, forward=forward)

        if action is None and not accept_missing:
            raise TypeError("Failed: lookup({!s}, {!r})".format(verb, typ))

    def fallback(self, verb, typ):
        if verb == PATTERN:
            return pattern.Unknown
        else:
            raise TypeError("Failed: lookup({!s}, {!r}); no fallback provided".format(verb, typ))

    def is_ambiguous(self, typ, threshold=pattern.Matches.always):
        pat = self.lookup(verb=PATTERN, typ=typ)
        return pattern.is_ambiguous(pat, threshold=threshold)
