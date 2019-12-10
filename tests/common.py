class Rules:
    def __init__(self, *rules):
        self.rules = rules

    def lookup(self, verb, typ, accept_missing=False):
        for rule in self.rules:
            result = rule(verb=verb, typ=typ, ctx=self)
            if result is not None:
                return result
        if accept_missing:
            return None
        else:
            raise RuntimeError("No rule for verb={}, typ={}".format(verb, typ))
