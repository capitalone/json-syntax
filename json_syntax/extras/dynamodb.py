"""
While the main suite is fairly complex, it's really not hard to construct a small, useful
translation.

AWS's DynamoDB decorates values to represent them in JSON. The rules for the decorations are
fairly simple, and we'd like to translate to and from Python objects.

The a Dynamo values look like this:

    {"BOOL": true}
    {"L": [{"N": "1.5"}, {"S": "apple"}]}

We will generate rules to convert Python primitive types, lists and attrs classes into
Dynamo types.

This will special case the kinds of sets Dynamo handles. In keeping with the principle of
least astonishment, it won't convert, e.g. ``Set[MyType]`` into a Dynamo list. This will
just fail because Dynamo doesn't actually support that. You could add a rule if that's the
correct semantics.

For boto3 users: you must use the **client**, not the resource.

    ddb = boto3.client('dynamodb')
    ddb.put_item(TableName='chair', Item=...)

The ``boto3.resource('dynamodb').Table`` is already doing a conversion step we don't want.

Ref: https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_AttributeValue.html#DDB-Type-AttributeValue-NS  # noqa
"""

from json_syntax.helpers import (
    issub_safe,
    NoneType,
    has_origin,
    get_origin,
    STR2PY,
    PY2STR,
)
from json_syntax.product import build_attribute_map
from json_syntax.string import stringify_keys
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
_STRING_ACTIONS = {DDB2PY: STR2PY, PY2DDB: PY2STR}


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
    A rule to represent numeric values as Dynamo numbers. Any number type should work,
    however both Decimal and float support NaN and infinity and I haven't tested these in
    Dynamo.
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
    if verb not in _STRING_ACTIONS or not has_origin(typ, dict, num_args=2):
        return
    (key_typ, val_typ) = typ.__args__
    inner_key = ctx.lookup(verb=_STRING_ACTIONS[verb], typ=key_typ)
    inner_val = ctx.lookup(verb=verb, typ=val_typ)
    if verb == DDB2PY:
        return partial(
            decode_dict, inner_key=inner_key, inner_val=inner_val, con=get_origin(typ)
        )
    elif verb == PY2DDB:
        return partial(encode_dict, inner_key=inner_key, inner_val=inner_val)


def sets(verb, typ, ctx):
    """
    A rule to represent sets. Will only use specialized Dynamo sets, to abide by principle
    of least astonishment.

    Valid python types include Set[Decimal], Set[str], Set[bytes], or FrozenSet for any of
    these. Also, any number that converts from Decimal and converts to a decimal if str is
    called should work.
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
    inner_map = build_attribute_map(verb, typ, ctx)
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
        """
        Gets a function to convert a DynamoDB structure to a Python object.

        This method is here for completeness; see ddb_item_to_python.
        """
        return self.lookup(verb=DDB2PY, typ=typ)

    def python_to_dynamodb(self, typ):
        """
        Gets a function to convert a Python object to a DynamoDB structure.

        This method is here for completeness; see python_to_ddb_item and ad_hoc.
        """
        return self.lookup(verb=PY2DDB, typ=typ)

    def ddb_item_to_python(self, typ):
        """
        Gets a function to convert a DynamoDB Item to a Python object.

        The `typ` argument must be an attrs class, but this method won't check that.

        Usage:

            rs = dynamodb_ruleset()
            response = client.get_item(TableName='my_table',
                                       Key=rs.ad_hoc(my_key='some_string'))
            decoder = rs.ddb_item_to_python(MyAttrsType)
            result = decoder(response['Item'])
        """
        inner = self.lookup(verb=DDB2PY, typ=typ)
        return partial(wrap_item, inner=inner)

    def python_to_ddb_item(self, typ):
        """
        Gets a function to convert a Python object to a DynamoDB Item.

        The `typ` argument must be an attrs class, but this method won't check that.

        Usage:

            rs = dynamodb_ruleset()
            encoder = rs.python_to_ddb_item(MyAttrsType)
            client.put_item(TableName='my_table', Item=encoder(my_item))
        """
        inner = self.lookup(verb=PY2DDB, typ=typ)
        return partial(unwrap_item, inner=inner)

    def ad_hoc(self, _key_prefix="", **kw):
        """
        Convenience method to encode an ad hoc set of arguments used in various DynamoDB
        APIs.

        If an argument is a tuple, it must be a two-item tuple of ``(value, type)``.
        If you want to use container types, you'll have to specify them fully. For empty
        dicts or lists, just use any type as the inner, e.g. ``({}, Dict[str, str])``.

        Example:

            rs = dynamodb_ruleset()
            client.update_item(
                TableName='my_table',
                Key=rs.ad_hoc(my_hash_key='some_string', my_int_key=77),
                UpdateExpression="SET counter=:my_int, info=:my_class, num=:my_float",
                ExpressionAttributeValue=rs.ad_hoc(
                   ':',  # indicates that keys are prefixed with :
                   my_int=5,
                   my_class=(instance, MyClass),
                   my_float=3.3,
                )
            )
        """
        out = {}
        for key, val in kw.items():
            if isinstance(val, tuple):
                enc = self.python_to_dynamodb(val[1])(val[0])
            else:
                enc = self.python_to_dynamodb(type(val))(val)
            out[_key_prefix + key] = enc
        return out


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
        stringify_keys,
        optionals,
        nulls,
        *extras,
        cache=cache
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


def decode_null(value):
    desigil(value, NULL=bool)
    return None


def encode_null(value):
    if not value:
        return {"NULL": True}
    else:
        raise ValueError("{} is not None".format(value))


def decode_boolean(value):
    _, value = desigil(value, BOOL=bool)
    return value


def encode_boolean(value):
    return {"BOOL": bool(value)}


b64decode = partial(b64.b64decode, validate=True)


def b64encode(value):
    return b64.b64encode(value).decode("ASCII")


def decode_binary(value):
    _, value = desigil(value, B=(str, bytes))
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
        # This is all the Real interface guarantees us. It's a stretch using Fraction in
        # Dynamo.
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


def encode_dict(value, inner_key, inner_val):
    return {"M": {inner_key(key): inner_val(val) for key, val in value.items()}}


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


def wrap_item(item, inner):
    return inner({"M": item})


def unwrap_item(value, inner):
    value = inner(value)
    _, item = desigil(value, M=dict)
    return item
