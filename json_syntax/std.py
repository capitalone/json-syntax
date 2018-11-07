'''
Standard converters.
'''

from .types import Convertable, Converter, Behavior, Trip, type_fqn

import attr
from decimal import Context
from typing import Sequence, Optional, _eval_type, _ForwardRef


@attr.s(frozen=True, auto_attrib=True)
class IdentityConverter(Converter):
    '''
    An IdentityConverter leaves the data untouched when it is known to be represented identically in both
    JSON and Python.
    '''
    specified = True
    subject: type

    def _behaviors(self):
        return Behavior.roundtrip(trip=Trip.PY_JS, subject=self.subject)

    def convert(self, value, subject, trip):
        return value


@attr.s(frozen=True, auto_attrib=True)
class NumericConverter(Converter):
    '''
    Numerics are complicated because of multiple representations on the JSON and Python side.

    Motivations:

    * JSON itself only recognizes decimal rationals.
    * Compliant JSON handlers may thus strip trailing zeroes and decimals points.
    * stdlib compatible handlers may distinguish between integers and decimal rationals, and create ``int`` or ``float``.
    * stdlib compatible handlers may recognize infinity and Nan constants.
    * stdlib compatible handlers will faithfully render Decimals with trailing zeroes and floats with at least ``.0``.
    * JSON handling may be outside the user's control.

    Thus, for rationals:

    * When reading, we should accept both rationals and integrals.
    * When writing, we should generate the rational type.
    * We provide separate constructors to allow use of methods like ``Context.create_decimal``.

    We can use the same logic for other types. Our standard converters simply accept any kind of Number on the JSON side.
    '''
    specified = True
    subject: type
    json_primary_type: type
    json_secondary_types: Sequence[type] = ()
    json_constructor: callable = attr.ib()
    python_constructor: callable = attr.ib()
    _instance_check: Tuple[type, ...] = attr.ib(init=False, repr=False)

    @json_constructor.default
    def _jc_default(self):
        return self.json_primary_type

    @python_constructor.default
    def _pc_default(self):
        return self.subject

    @_instance_check.default
    def _instance_calc(self):
        return (self.json_primary_type,) + tuple(self.json_secondary_type)

    def _behaviors(self):
        return Behavior.roundtrip(trip=Trip.PY_JS, subject=self.subject)

    def can_attempt(self, value, subject, trip):
        if trip == Trip.PY_JS:
            return isinstance(value, subject)
        elif trip == Trip.JS_PY:
            return isinstance(value, self._instance_check)
        else:
            raise InvalidTripArgument()

    def convert(self, value, subject, trip):
        if trip == Trip.PY_JS:
            return self.json_constructor(value)
        elif trip == Trip.JS_PY:
            return self.python_constructor(value)
        else:
            raise InvalidTripArgument()


@attr.s(frozen=True)
class AttrConvertable(Converter):
    specified = False
    subject = attr.ib()

    def _behaviors(self):
        return  Behavior(trip=trip, subject=attribute.type)


@attr.s(auto_attribs=True, frozen=True)
class AttrsDictConverter(Converter):
    '''
    Constructs a converter that delegates to its parameters.
    '''
    specified = True
    subject: type = attr.ib()

    @params.default
    def _calc_params(self):
        _params = {}
        for field in attr.fields(self.subject):
            _params[field.name] = AttrConvertable(field)


def get_attrs_hints(cls):
    '''
    The typing module provides get_type_hints, but it only inspects annotations.
    attrs classes that use ``attr.ib(type=...)`` should work.
    '''
    globalns = sys.modules[cls.__module__].__dict__
    hints = {}
    for attrib in attr.fields(cls):
        name = attrib.name
        value = attrib.type
        hints[name] = normalize(value, globals=globalns)


string_identity = IdentityConverter(str)
none_identity = IdentityConverter(type(None))
bool_identity = IdentityConverter(bool)

use_floats_for_floats = NumericConverter(float, json_primary_type=float, json_secondary_types=[Number])
use_decimals_for_decimals = NumericConverter(Decimal, json_primary_type=Decimal, json_secondary_types=[Number])
use_ints_for_ints = NumericConverter(int, json_primary_type=int, json_secondary_types=[Number])


def use_decimals_with_context(context):
    return NumericConverter(Decimal,
                            json_primary_type=Decimal,
                            json_secondary_types=[Number],
                            json_constructor=context.create_decimal,
                            python_constructor=context.create_decimal)
