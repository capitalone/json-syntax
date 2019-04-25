"""
Patterns to represent roughly what syntax will look like, and also to investigate whether
unions are potentially ambiguous.
"""
from functools import partial, lru_cache, singledispatch
from itertools import chain, cycle, islice, product, zip_longest
from enum import IntEnum

try:
    import simplejson as json
except ImportError:
    import json

    def _def(obj):
        return obj.for_json()

    _args = {"default": lambda obj: obj.for_json()}
else:
    _args = {"for_json": True}

dump = partial(json.dump, **_args)
dumps = partial(json.dumps, **_args)


class Matches(IntEnum):
    """
    This determines the degree to which one pattern can shadow another causing potential ambiguity.

    Meaning:

      * always: The pattern always shadows the other pattern.
      * sometimes: The pattern is known to sometimes shadow another pattern.
      * potential: It's not possible to prove the pattern won't shadow the other pattern.
      * never: The pattern will never shadow the other pattern.

    In determining ambiguity, a `sometimes` threshold is often permissible. For example, if you have
    `Union[date, str]` then properly formatted dates will sometimes shadow strings. That's probably okay
    if you want special handling for dates.

    But in `Union[str, date]`, the `str` will always match and thus no dates will ever be recognized.
    """

    always = 0
    sometimes = 1
    potential = 2
    never = 3


matches_all = partial(max, default=Matches.always)
matches_any = partial(min, default=Matches.never)


def matches(left, right, ctx=None):
    """
    Given two `Pattern` objects, determine if the `left` pattern shadows the `right`.

    Returns a `Matches` instance.
    """
    if ctx is None:
        ctx = set()
    else:
        if (left, right) in ctx:
            return Matches.potential
    ctx.add((left, right))
    result = matches_any(
        left._matches(right, ctx)
        for left, right in product(left._unpack(), right._unpack())
    )
    return result


class Pattern:
    def _matches(self, other, ctx):
        raise NotImplementedError()

    def _unpack(self):
        return [self]

    def __repr__(self):
        return dumps(self, indent=2)


class Atom(Pattern):
    def __init__(self, value):
        self.value = value

    def for_json(self):
        return self.value

    def _matches(self, other, ctx):
        return (
            Matches.always
            if isinstance(other, Atom) and self.value == other.value
            else Matches.never
        )


class String(Pattern):
    """
    Rather than try to analyze regular expressions, we just name common string patterns,
    and have a list of known ambiguities.

    We're deliberately not trying to analyze regexes here as we assume you would want to
    use specialize logic to make such fine distinctions.
    """

    def __init__(self, name, arg=None):
        self.name = name
        self.arg = arg

    def for_json(self):
        if self.name == "exact":
            return "=" + self.arg
        else:
            return self.name

    @classmethod
    def exact(cls, string):
        assert isinstance(string, str)
        return cls("exact", string)

    def _matches(self, other, ctx):
        "Check whether this pattern will match the other."
        if not isinstance(other, String):
            return Matches.never
        if self.name == "str":
            return Matches.always  # Strings always overshadow
        elif other.name == "str":
            return Matches.sometimes  # Strings are sometimes shadowed
        if self.name == "exact":
            if other.name == "exact":
                return Matches.always if self.arg == other.arg else Matches.never
            elif other.arg is None:
                return Matches.potential
            else:
                return Matches.always if other.arg(self.arg) else Matches.never
        return Matches.always if self.name == other.name else Matches.potential


class _Unknown(Pattern):
    def __init__(self, name, match):
        self._name = name
        self._match = match

    def _matches(self, other, ctx):
        return self._match

    def __repr__(self):
        return self._name


String.any = String("str")
Number = Atom(0)
Null = Atom(None)
Bool = Atom(False)
Missing = _Unknown("<missing>", Matches.never)
Unknown = _Unknown("<unknown>", Matches.potential)


class Alternatives(Pattern):
    """
    Used by the `show_pattern` verb to represent alternative patterns in unions.
    """

    def __init__(self, alts):
        self.alts = tuple(alts)
        assert all(isinstance(alt, Pattern) for alt in self.alts)

    def _unpack(self):
        yield from self.alts

    def _matches(self, other, ctx):
        raise NotImplementedError(
            "Didn't call unpack"
        )  # Should be bypassed by _unpack.

    def for_json(self):
        out = ["alts"]
        out.extend(self.alts)
        return out


class Array(Pattern):
    def __init__(self, elems, *, homog):
        self.elems = tuple(elems)
        assert all(isinstance(elem, Pattern) for elem in self.elems)
        self._homog = homog

    @classmethod
    def homog(cls, elem):
        return cls((elem,), homog=True)

    @classmethod
    def exact(cls, elems):
        return cls(elems, homog=False)

    def _matches(self, other, ctx):
        if not isinstance(other, Array):
            return Matches.never
        if self._homog and not other.elems:
            return Matches.always
        left = self.elems
        right = other.elems
        if self._homog and not other._homog:
            left = islice(cycle(left), len(right))
        elif not self._homog and other._homog:
            right = islice(cycle(right), len(left))

        possible = matches_all(
            matches(l, r, ctx) for l, r in zip_longest(left, right, fillvalue=Missing)
        )
        if self._homog and other._homog:
            # Zero cases can't be distinguished match.
            possible = matches_any([Matches.sometimes, possible])
        return possible

    def for_json(self):
        out = list(self.elems)
        if self.homog:
            out.append("...")
        return out


class Object(Pattern):
    def __init__(self, items, *, homog):
        self.items = tuple(items)
        valid = all(
            isinstance(key, Pattern) and isinstance(val, Pattern)
            for key, val in self.items
        )
        if not valid:
            # for key, val in self.items:
            #     print(f"{key!r}: {type(key)} / {val!r}: {type(val)}")
            raise TypeError("Keys and values must be patterns")
        self._homog = homog

    @classmethod
    def homog(cls, key, val):
        return cls(((key, val),), homog=True)

    @classmethod
    def exact(cls, items):
        return cls(items, homog=False)

    def _matches(self, other, ctx):
        if not isinstance(other, Object):
            return Matches.never
        if self._homog and not other.items:
            return Matches.always

        possible = matches_all(
            matches_any(
                matches(lk, rk, ctx) and matches(lv, rv, ctx) for rk, rv in other.items
            )
            for lk, lv in self.items
        )
        if self._homog and other._homog:
            possible = matches_any([Matches.sometimes, possible])
        return possible

    def for_json(self):
        def jsonify(key):
            try:
                for_json = key.for_json
            except AttributeError:
                return key
            else:
                return for_json()

        out = {jsonify(k): v for k, v in self.items}
        if self._homog:
            out["..."] = "..."
        return out


@singledispatch
def is_ambiguous(pattern, threshold=Matches.always, _path=()):
    """
    Attempts to determine if alternatives within a pattern create ambiguities given
    a threshold. The `json_syntax.RuleSet.is_ambiguous` constructs the `Pattern` instances
    and calls this for you, though.

    If an ambiguity is found, this attempts to identify the path within the pattern to
    find it. (This feature isn't well tested, though.)
    """
    raise TypeError("pattern must be a recognized subclass of Pattern.")


@is_ambiguous.register(Atom)
@is_ambiguous.register(String)
def _(pattern, threshold=Matches.always, _path=()):
    return ()


@is_ambiguous.register(_Unknown)
def _(pattern, threshold=Matches.always, _path=()):
    return (str(pattern),) if pattern._match <= threshold else ()


def _any(iterable):
    for item in iterable:
        if bool(item):
            return item
    return ()


@is_ambiguous.register(Array)
def _(pattern, threshold=Matches.always, _path=()):
    _path += ("[]",)
    return _any(is_ambiguous(elem, threshold, _path) for elem in pattern.elems)


@is_ambiguous.register(Object)
def _(pattern, threshold=Matches.always, _path=()):
    return _any(
        is_ambiguous(val, threshold, _path + (str(key),)) for key, val in pattern.items
    )


@is_ambiguous.register(Alternatives)
def _(pattern, threshold=Matches.always, _path=()):
    # An ambiguous pattern is one where an earlier pattern shadows a later pattern.
    alts = pattern.alts
    for i, early in enumerate(alts[:-1]):
        for late in alts[i + 1 :]:
            if matches(early, late) <= threshold:
                return _path + ("alternative {}".format(i),)

    return ()
