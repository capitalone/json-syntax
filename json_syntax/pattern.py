"""
Patterns to represent roughly what syntax will look like, and also to investigate whether
unions are potentially ambiguous.
"""
from functools import partial, lru_cache
from enum import IntEnum

try:
    import simplejson as json
except ImportError:
    import json

    def _def(obj):
        return obj.for_json()
    _args = {'default': lambda obj: obj.for_json()}
else:
    _args = {'for_json': True}

dump = partial(json.dump, **_args)
dumps = partial(json.dumps, **_args)


class Matches(IntEnum):
    '''
    This determines the degree to which one pattern can shadow another causing potential ambiguity.
    '''
    always = 0  # Will always match
    sometimes = 1  # It will sometimes match
    potential = 2  # Can't prove it won't match
    never = 3  # Provably won't match


@lru_cache(32)
def _reduce(left, right, reverse):
    consider = (left, right)
    seq = Matches
    if reverse:
        seq = reversed(seq)
    for val in seq:
        if val in consider:
            return val
    raise ValueError("Can't reduce against unknown type")


def _match_many(source, *, pos):
    "Combine matches where all elements must match."
    result = Matches.always if pos else Matches.never
    stop = Matches.never if pos else Matches.always
    for match in source:
        result = _reduce(result, match, reverse=pos)
        if result == stop:
            break
    return result


match_all = partial(_match_many, pos=True)
match_any = partial(_match_many, pos=False)


def matches(left, right, ctx=None):
    if ctx is None:
        ctx = (set(), set())
    else:
        if left in ctx[0] or right in ctx[1]:
            return Matches.never
    ctx[0].add(left)
    ctx[1].add(right)
    return match_any(left._matches(right, ctx) for left, right
                     in product(left._unpack(), right._unpack()))


class Pattern:
    def _matches(self, other, ctx):
        raise NotImplementedError()

    def _unpack(self):
        return [self]

    def __repr__(self):
        return dumps(self, indent=2)


class Atom:
    def __init__(self, value):
        self.value = value

    def _matches(self, other, ctx):
        return isinstance(other, Atom) and self.value == other.value


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
        if name == 'exact':
            return '=' + arg
        else:
            return name

    def _matches(self, other, ctx):
        "Check whether this pattern will match the other."
        if not isinstance(other, StringPattern):
            return Matches.never
        if self.name == 'str':
            return Matches.always  # Strings always overshadow
        elif other.name == 'str':
            return Matches.sometimes  # Strings are sometimes shadowed
        if self.name == 'exact':
            if other.name == 'exact':
                return Matches.always if self.arg == other.arg else Matches.never
            elif other.arg is None:
                return Matches.potential
            else:
                return Matches.always if other.arg(self.arg) else Matches.never
        return Matches.always if self.name == other.name else Matches.potential


class _Missing(Pattern):
    def _matches(self, other, ctx):
        return Matches.never

    def __repr__(self):
        return '<missing>'


String.any = String('str')
Number = Atom(0)
Null = Atom(None)
Bool = Atom(False)
Missing = _Missing()


class Alternatives(Pattern):
    """
    Used by the `show_pattern` verb to represent alternative patterns in unions.
    """

    def __init__(self, alts):
        self.alts = tuple(alts)

    def _unpack(self):
        yield from self.alts

    def _matches(self, other, ctx):
        raise NotImplementedError("Didn't call unpack")  # Should be bypassed by _unpack.

    def for_json(self):
        out = ['alts']
        out.extend(self.alts)
        return out


class Array(Pattern):
    def __init__(self, elems, *, homog):
        self.elems = tuple(elems)
        self.homog = homog

    @classmethod
    def homog(cls, elem):
        return cls((elem,), homog=True)

    @classmethod
    def exact(cls, elems):
        return cls(elems, homog=False)

    def _matches(self, other, ctx):
        if not isinstance(other, Array):
            return Matches.never
        left = self.elems
        right = other.elems
        if self.homog and not other.homog:
            left = cycle(left)
        elif not self.homog and other.homog:
            right = cycle(right)

        return matches_all(
            matches(l, r, ctx) for l, r
            in zip_longest(left, right, fillvalue=Missing)
        )

    def for_json(self):
        out = ['...'] if self.homog else ['exact']
        out.extend(self.elems)
        return out


class Object(Pattern):
    def __init__(self, items, *, homog):
        self.items = tuple(items)
        self.homog = homog

    @classmethod
    def homog(cls, key, val):
        return cls(((key, val),), homog=True)

    @classmethod
    def exact(cls, items):
        return cls(items, homog=False)

    def _matches(self, other, ctx):
        if not isinstance(other, Object):
            return Matches.never

        return matches_all(
            matches_any(
                matches(l, r, ctx)
                for r in right
            ) for l in left
        )

    def for_json(self):
        out = dict(self.items)
        if self.homog:
            out['...'] = '...'
        return out
