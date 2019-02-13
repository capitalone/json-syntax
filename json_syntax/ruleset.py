from .cache import SimpleCache

import logging

logger = logging.getLogger(__name__)
TRACE = 5


class RuleSet:
    def __init__(self, *rules, cache=None):
        self.rules = rules
        self.cache = cache or SimpleCache()

    def lookup(self, verb, typ, accept_missing=False):
        logger.log(TRACE, "lookup(%s, %r): start", verb, typ)
        if typ is None:
            if not accept_missing:
                raise TypeError(f"Attempted to find {verb} for 'None'")
            return self.fallback(verb=verb, typ=typ)

        action = self.cache.get(verb=verb, typ=typ)
        if action is not None:
            logger.log(TRACE, "lookup(%s, %r): cached", verb, typ)
            return action

        forward = self.cache.in_flight(verb=verb, typ=typ)

        try:
            for rule in self.rules:
                action = rule(verb=verb, typ=typ, ctx=self)
                if action is not None:
                    self.cache.complete(verb=verb, typ=typ, action=action)
                    logger.log(TRACE, "lookup(%s, %r): computed", verb, typ)
                    return action

            logger.log(TRACE, "lookup(%s, %r): fallback", verb, typ)
            action = self.fallback(verb=verb, typ=typ)
            if action is not None:
                self.cache.complete(verb=verb, typ=typ, action=action)
                logger.log(TRACE, "lookup(%s, %r): computed by fallback", verb, typ)
                return action
        finally:
            self.cache.de_flight(verb=verb, typ=typ, forward=forward)

    def fallback(self, verb, typ):
        pass
