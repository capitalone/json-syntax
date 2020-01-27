from importlib import import_module


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


class SoftMod:
    def __init__(self, *modules, allow_SyntaxError=False):
        self.mods = mods = []
        for name in modules:
            try:
                mods.append(import_module(name))
            except ImportError:
                pass
            except SyntaxError:
                if not allow_SyntaxError:
                    raise

    def __getattr__(self, name):
        for mod in self.mods:
            val = getattr(mod, name, None)
            if val is not None:
                return val
        return None


typing = SoftMod("typing", "typing_extensions")
dataclasses = SoftMod("dataclasses")
