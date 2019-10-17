"""
While the main suite is fairly complex, it's really not hard to construct a small, useful translation.

AWS's DynamoDB decorates values to represent them in JSON. The rules for the decorations are fairly simple, and we'd
like to translate to and from Python objects.

The a Dynamo values look like this:

    {"BOOL": true}
    {"L": [{"N": "1.5"}, {"S": "apple"}]}

We will generate rules to convert Python primitive types, lists and attrs classes into Dynamo types.

This will special case the kinds of sets Dynamo handles. In keeping with the principle of least astonishment,
it won't convert, e.g. ``Set[MyType]`` into a Dynamo list. This will just fail because Dynamo doesn't actually
support that. You could add a rule if that's the correct semantics.

For boto3 users: you must use the **client**, not the resource.

    ddb = boto3.client('dynamodb')
    ddb.put_item(TableName='chair', Item=...)

The ``boto3.resource('dynamodb').Table`` is already doing a conversion step we don't want.

Ref: https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_AttributeValue.html#DDB-Type-AttributeValue-NS
"""

from json_syntax.helpers import issub_safe, NoneType, has_origin, get_origin
from json_syntax.product import build_attribute_map
from json_syntax.ruleset import SimpleRuleSet

import base64 as b64
from decimal import Decimal
from enum import Enum
from functools import partial
from math import isfinite
from numbers import Real
from typing import Union

DDB2PY = "dynamodb_to_python"
PY2DDB = "python_to_dynamodb"


def booleans(verb, typ, ctx):
    """
    A rule to represent boolean values as Dynamo booleans.
    """
    if typ != bool:
        return
    if verb == DDB2PY:
        return decode_boolean
    elif verb == PY2DDB:
        return encode_boolean


def numbers(verb, typ, ctx):
    """
    A rule to represent numeric values as Dynamo numbers. Any number type should work, however both Decimal and float
    support NaN and infinity and I haven't tested these in Dynamo.
    """
    if typ == bool or not issub_safe(typ, (Decimal, Real)):
        return
    if verb == DDB2PY:
        return partial(decode_number, typ=typ)
    elif verb == PY2DDB:
        return encode_number


def strings(verb, typ, ctx):
    """
    A rule to represent string values as Dynamo strings.
    """
    if typ != str:
        return
    if verb == DDB2PY:
        return decode_string
    elif verb == PY2DDB:
        return encode_string


def enums(verb, typ, ctx):
    "Rule to convert between enumerated types and strings."
    if issub_safe(typ, Enum):
        if verb == PY2DDB:
            return encode_enum
        elif verb == DDB2PY:
            return partial(decode_enum, typ=typ)


def binary(verb, typ, ctx):
    """
    A rule to represent bytes as Dynamo binary values.
    """
    if typ != bytes:
        return
    if verb == DDB2PY:
        return decode_binary
    elif verb == PY2DDB:
        return encode_binary


def lists(verb, typ, ctx):
    """
    A rule to represent lists as Dynamo list values.
    """
    if has_origin(typ, list, num_args=1):
        (inner,) = typ.__args__
    elif has_origin(typ, tuple, num_args=2):
        (inner, ell) = typ.__args__
        if ell is not Ellipsis:
            return
    else:
        return
    inner = ctx.lookup(verb=verb, typ=inner)
    if verb == DDB2PY:
        return partial(decode_list, inner=inner, typ=get_origin(typ))
    elif verb == PY2DDB:
        return partial(encode_list, inner=inner)


def dicts(verb, typ, ctx):
    """
    A rule to represent lists as Dynamo list values.
    """
    if not has_origin(typ, dict, num_args=2):
        return
    (key_typ, val_typ) = typ.__args__
    if key_typ != str:
        return

    inner = ctx.lookup(verb=verb, typ=val_typ)
    if verb == DDB2PY:
        return partial(decode_dict, inner_key=str, inner_val=inner, con=get_origin(typ))
    elif verb == PY2DDB:
        return partial(encode_dict, inner=inner)


def sets(verb, typ, ctx):
    """
    A rule to represent sets. Will only use specialized Dynamo sets, to abide by principle of least astonishment.

    Valid python types include Set[Decimal], Set[str], Set[bytes], or FrozenSet for any of these. Also, any number that
    converts from Decimal and converts to a decimal if str is called should work.
    """
    if not has_origin(typ, (set, frozenset), num_args=1):
        return
    (inner,) = typ.__args__
    con = get_origin(typ)
    if inner == bytes:
        if verb == DDB2PY:
            return partial(decode_binary_set, con=con)
        elif verb == PY2DDB:
            return encode_binary_set

    if inner != bool and issub_safe(inner, (Decimal, Real)):
        if verb == DDB2PY:
            return partial(decode_number_set, elem=inner, con=con)
        elif verb == PY2DDB:
            return encode_number_set

    if inner == str:
        if verb == DDB2PY:
            return partial(decode_string_set, con=con)
        elif verb == PY2DDB:
            return encode_string_set


def attrs(verb, typ, ctx):
    """
    A rule to represent attrs classes. This isn't trying to support hooks or any of that.
    """
    inner_map = build_attribute_map(verb, typ, ctx, read_all=verb == PY2DDB)
    if inner_map is None:
        return

    if verb == DDB2PY:
        return partial(decode_map, inner_map=inner_map, con=typ)
    elif verb == PY2DDB:
        return partial(encode_map, inner_map=inner_map)


def nulls(verb, typ, ctx):
    """
    A rule to represent boolean values as Dynamo nulls.
    """
    if typ != NoneType:
        return
    if verb == DDB2PY:
        return decode_null
    elif verb == PY2DDB:
        return encode_null


def optionals(verb, typ, ctx):
    """
    Handle an ``Optional[inner]`` by passing ``None`` through.
    """
    if has_origin(typ, Union, num_args=2):
        if NoneType not in typ.__args__:
            return
        inner = None
        for arg in typ.__args__:
            if arg is not NoneType:
                inner = arg
        if inner is None:
            raise TypeError("Could not find inner type for Optional: " + str(typ))
    else:
        return
    inner = ctx.lookup(verb=verb, typ=inner)
    if verb == DDB2PY:
        return partial(decode_optional, inner=inner)
    elif verb == PY2DDB:
        return partial(encode_optional, inner=inner)


class DynamodbRuleSet(SimpleRuleSet):
    def dynamodb_to_python(self, typ):
        return self.lookup(verb=DDB2PY, typ=typ)

    def python_to_dynamodb(self, typ):
        return self.lookup(verb=PY2DDB, typ=typ)


def dynamodb_ruleset(
    strings=strings,
    numbers=numbers,
    booleans=booleans,
    binary=binary,
    lists=lists,
    attrs=attrs,
    enums=enums,
    sets=sets,
    dicts=dicts,
    optionals=optionals,
    extras=(),
    custom=DynamodbRuleSet,
    cache=None,
):
    """
    Constructs a RuleSet to migrate data to and from DynamoDB.
    """
    return custom(
        strings,
        numbers,
        booleans,
        binary,
        lists,
        attrs,
        enums,
        sets,
        dicts,
        optionals,
        *extras,
        cache=cache,
    )


def desigil(value, **sigils):
    """
    Parse a ``{sigil: value}`` expression and unpack the value inside.
    """
    if isinstance(value, dict) and len(value) == 1:
        for sig, typ in sigils.items():
            try:
                inner = value[sig]
            except KeyError:
                pass
            else:
                if not isinstance(inner, typ):
                    raise ValueError(
                        "This Dynamo value {} must have a member encoded as type {}".format(
                            sig, typ.__name__
                        )
                    )
                return sig, inner
    for sig, typ in sigils.items():
        break
    raise ValueError(
        "This Dynamo value must be encoded as a single-item dict {%r: %s}"
        % (sig, typ.__name__)
    )


def decode_optional(value, inner):
    try:
        desigil(value, NULL=bool)
    except ValueError:
        return inner(value)
    else:
        return None


def encode_optional(value, inner):
    if value is None:
        return {"NULL": True}
    else:
        return inner(value)


def decode_boolean(value):
    _, value = desigil(value, BOOL=bool)
    return value


def encode_boolean(value):
    return {"BOOL": bool(value)}


b64decode = partial(b64.b64decode, validate=True)


def b64encode(value):
    return b64.b64encode(value).decode("ASCII")


def decode_binary(value):
    _, value = desigil(value, B=str)
    return b64decode(value)


def encode_binary(value):
    return {"B": b64encode(value)}


def decode_number(value, typ):
    _, value = desigil(value, N=str, S=str)
    return typ(value)


def _encode_number(value):
    if not isfinite(value):
        # We could employ a string type here, but this could put us in a corner if we
        # try to use number sets...
        raise ValueError("Can't encode non-finite values in Dynamodb")
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    else:
        # This is all the Real interface guarantees us. It's a strech using Fraction in Dynamo.
        return str(float(value))


def encode_number(value):
    return {"N": _encode_number(value)}


def decode_string(value):
    _, value = desigil(value, S=str)
    return value


def encode_string(value):
    return {"S": str(value)}


def decode_enum(value, typ):
    _, value = desigil(value, S=str)
    return typ[value]


def encode_enum(value):
    return {"S": value.name}


def decode_list(value, inner, typ):
    _, value = desigil(value, L=list)
    return typ(map(inner, value))


def encode_list(value, inner):
    return {"L": list(map(inner, value))}


def decode_dict(value, inner_key, inner_val, con):
    _, value = desigil(value, M=dict)
    return con(((inner_key(key), inner_val(val)) for key, val in value.items()))


def encode_dict(value, inner):
    return {"M": {str(key): inner(val) for key, val in value.items()}}


def decode_map(value, inner_map, con):
    _, value = desigil(value, M=dict)
    args = {}
    for attr in inner_map:
        try:
            arg = value[attr.name]
        except KeyError:
            if attr.is_required:
                raise KeyError("Missing key") from None
        else:
            args[attr.name] = attr.inner(arg)
    return con(**args)


def encode_map(value, inner_map):
    out = {}
    for attr in inner_map:
        field = getattr(value, attr.name)
        if field == attr.default:
            continue
        out[attr.name] = attr.inner(field)
    return {"M": out}


def decode_binary_set(value, con):
    _, value = desigil(value, BS=list)
    return con(map(b64decode, value))


def encode_binary_set(value):
    return {"BS": list(map(b64encode, value))}


def decode_number_set(value, con, elem):
    _, value = desigil(value, NS=list)
    return con(map(elem, value))


def encode_number_set(value):
    return {"NS": list(map(_encode_number, value))}


def decode_string_set(value, con):
    _, value = desigil(value, SS=list)
    return con(map(str, value))


def encode_string_set(value):
    return {"SS": list(map(str, value))}
