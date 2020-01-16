[![CircleCI](https://circleci.com/gh/UnitedIncome/json-syntax/tree/master.svg?style=svg)](https://circleci.com/gh/UnitedIncome/json-syntax/tree/master)

# json-syntax

A Python library to translate between JSON compatible structures and native Python
classes using customizable rules.

## Use case

If you're like the authors, you tried writing a encoding function that attempted to
encode and decode by interrogating the types at runtime, maybe calling some method like
`asdict`. This works fine for generating JSON, but it gets sketchy<sup
id="a1">[1](#f1)</sup> when trying to decode the same JSON.

Further, we have annotations in Python 3! Even if you're not using a type checker, just
labeling the types of fields makes complex data structures far more comprehensible.

This library is aimed at projects that have a complex JSON schema that they're trying to
structure using libraries like [attrs][].

 * It exploits [gradual typing][] via annotations, [typing][] and [dataclasses][]
 * It expects classes to be *statically* described using types
    * But a fallback can be provided to handle data described at runtime
    * It provides hooks to normalize legacy inputs
 * It makes it trivial to extend the library with your own rules
    * Actions and Rules are simply functions
    * Encoders and decoders can be pickled
 * The library has no dependencies of its own
    * It does not actually read or write JSON

### Supported types

 * Atoms including `None`, `bool`, `int`, `float`, `str`.
    * Floats may optionally be represented as strings.
 * The `decimal.Decimal` class, represented as itself or in string form.
 * The `datetime.date` and `datetime.datetime` classes, represented in ISO8601 form.
 * Preliminary support for `datetime.timedelta` as ISO8601 time durations.
 * Subclasses of `enum.Enum`, represented by the string names.
    * Also, a `faux_enums` rule will accept an Enum type if you just use strings in your
      code.
 * The `typing.Optional[E]` type allows a JSON `null` to be substituted for a value.
 * Collections including `typing.List[E]`, `typing.Tuple[E, ...]`, `typing.Set[E]` and
   `typing.FrozenSet[E]`.
    * The `...` is [literal][ellipsis] and indicates a homogenous tuple, essentially a
      frozen list.
 * The `typing.Dict[K, V]` type allows a JSON object to represent a homogenous `dict`.
    * Restriction: the keys must be strings, ints, enums or dates.
 * **New**: The `typing.TypedDict` type allows a JSON object to represent a `dict` with specific
   keys.
 * Python classes implemented using `attrs.attrs`, `dataclasses.dataclass` are
   represented as JSON dicts and
 * Named tuples via `typing.NamedTuple` and heterogenous tuples via `typing.Tuple`.
    * Though, you should consider converting these to `dataclass`.
 * The `typing.Union[A, B, C]` rule will recognize alternate types by inspection.

In addition, `dataclass` and `attrs` classes support hooks to let you completely customize
their JSON representation.

### Extras

These were originally intended as examples for how to use the package, but they're potentially
useful in their own right.

 * [A ruleset][extras ddb] for use with AWS DynamoDB is included with basic facilities.
   * Restriction: No general support for `typing.Union`, only `Optional`.
   * Restriction: No general support for `Set`, only the special cases that are native to DynamoDB.
 * [A `Flag` psuedo-type][extras flag] allows you to use regular strings directly as flags.
 * [A rule][extras loose] that will accept a complete `datetime` and return a `date` by truncating the timestamp.

## Usage

This example is also implemented in unit tests. First, let's declare some classes.

```python
import json_syntax as syn
from dataclasses import dataclass  # attrs works too
from decimal import Decimal
from datetime import date
from enum import Enum

@dataclass
class Account:
    user: str
    transactions: List['Trans']  # Forward references work!
    balance: Decimal = Decimal()

class TransType(Enum):
    withdraw = 0
    deposit = 1

@dataclass
class Trans:
    type: TransType
    amount: Decimal
    stamp: date
```

We'll next set up a RuleSet and use it to construct an encoder. The `std_ruleset`
function is a one-liner with some reasonable overrides. Here, we've decided that because
some intermediate services don't reliably retain decimal values, we're going to
represent them in JSON as strings.

```python
>>> rules = syn.std_ruleset(decimals=syn.decimals_as_str)
>>> encode_account = rules.python_to_json(typ=Account)
>>> decode_account = rules.json_to_python(typ=Account)
```

The RuleSet examines the type and verb, searches its list of Rules, and then uses the
first one that handles that type and verb to produce an Action.

For example, `attrs_classes` is a Rule that recognizes the verbs `python_to_json` and
`json_to_python` and will accept any class decorated with `@attr.s` or `@dataclass`.

It will scan the fields and ask the RuleSet how to encode them. So when it sees
`Account.user`, the `atoms` rule will match and report that converting a `str` to JSON
can be accomplished by simply calling `str` on it. The action it returns will literally
be the `str` builtin.

Thus `attrs_classes` will build a list of attributes on `Account` and actions to convert
them, and constructs an action to represent them.

```python
>>> sample_value = Account(
...     'bob', [
...         Trans(TransType.withdraw, Decimal('523.33'), date(2019, 4, 4))
...     ], Decimal('77.00')
... )

>>> encode_account(sample_value)
{
  'user': 'bob',
  'transactions': [
    {
      'type': 'withdraw',
      'amount': '523.33',
      'stamp': '2019-04-04'
    }
  ], 'balance': '77.00'
}
```

#### Encoding and decoding

The aim of all this is to enable reliable usage with your preferred JSON library:

```python
with open('myfile.json', 'r') as fh:
    my_account = decode_account(json.load(fh))

with open('myfile.json', 'w') as fh:
    json.dump(encode_account(my_account))
```

### Using generic types

Generally, the [typing][] module simple provides capital letter type names that obviously
correspond to the internal types. [See TYPES for a more thorough introduction][types].

And you specify the type of the contents as a parameter in square brackets.

Thus we have:

 * `list` and `List[E]`
 * `set` and `Set[E]`
 * `tuple` and `Tuple[E, ...]` is a special case!
 * `frozenset` and `FrozenSet[E]`
 * `dict` and `Dict[K, V]`

Tuple is a special case. In Python, they're often used to mean "frozenlist", so
`Tuple[E, ...]` (the `...` is [the Ellipsis object][ellipsis]) indicates all elements have
the type `E`.

They're also used to represent an unnamed record. In this case, you can use
`Tuple[A, B, C, D]` or however many types. It's generally better to use a `dataclass`.

The standard rules don't support:

 1. Using abstract types like `Iterable` or `Mapping`.
 2. Using type variables.
 3. Any kind of callable, coroutine, file handle, etc.

#### Support for deriving from Generic

There is experimental support for deriving from `typing.Generic`. An `attrs` or `dataclass`
may declare itself a generic class. If another class invokes it as `YourGeneric[Param,
Param]`, those `Param` types will be substituted into the fields during encoding. This is
useful to construct parameterized container types. Example:

    @attr.s(auto_attribs=True)
    class Wrapper(Generic[T, M]):
        body: T
        count: int
        messages: List[M]

    @attr.s(auto_attribs=True)
    class Message:
        first: Wrapper[str, str]
        second: Wrapper[Dict[str, str], int]

#### Unions

A union type lets you present alternate types that the converters will attempt in
sequence, e.g. `typing.Union[MyType, int, MyEnum]`.

This is implemented in the `unions` rule as a so-called<sup id="a2">[2](#f2)</sup>
undiscriminated union. It means the module won't add any additional information to the
value such as some kind of explicit tag.

When converting from Python to JSON, the checks are generally just using `isinstance`,
but when converting from JSON to Python, the check may be examining strings and `dict`
fields.

Thus, ambiguous values, especially JSON representations, may confuse the decoder.
See the section on [sharp edges][sharp] for more details.

### Hooks

We'll first examine decode and encode hooks. These let us entirely rewrite the JSON
representation before the normal logic is applied.

Let's suppose our `Account` class used to named the `balance` field `bal` and we need to
support legacy users.

```python
@dataclass
class Account:
    @classmethod
    def __json_pre_decode__(cls, value):
        if 'bal' in value:
            value = dict(value)
            value['balance'] = value.pop('bal')
        return value

    def __json_post_encode__(self, value):
        return dict(value, bal=value['balance'])

    ...
```

When we decode the value, the following sequence of steps takes place:

 1. `__json_pre_decode__` is called with `{'user': 'bob', 'bal': '77.0', ...}` and it
    returns `{'user': 'bob', 'balance': '77.0', ...}`
 2. Decoders are called against `user` and `balance` and the other fields
 3. The resulting dictionary is passed to `Account(**result)` to construct the instance.

During encoding, the reverse sequence takes place:

 1. The instance's fields are read and passed to encoders.
 2. The values are combined into a `dict`.
 3. `__json_post_encode__` is called with `{'user': 'bob', 'balance': '77.0', ...}` and
    can adjust the field name to `bal`.

#### JSON type check hook

Type checks are only used in _json-syntax_ to support `typing.Union`; in a nutshell, the
`unions` rule will inspect some JSON to see which variant is present.

If a type-check hook is not defined, `__json_pre_decode__` will be called before the
standard check is completed. (The standard check attempts to determine if required
fields are present and have the correct type.)

If you have information that can determine the type faster, a check hook can help.

Going back to our Account example, suppose we decide to support multiple account types
through a special ``class`` field. This is faster and more robust.

```python
class AbstractAccount:
    @classmethod
    def __json_check__(cls, value):
        return isinstance(value, dict) and value.get('class') == cls.__name__

@dataclass
class AccountA(AbstractAccount):
    ...

encode_account = rules.lookup(typ=Union[AccountA, AccountB, AccountC],
                              verb='python_to_json')
```

### Adding custom rules

See [the extras][] for details on custom rules, but generally a rule is just a
function. Say, for instance, your type has class methods that encode and decode, this
would be sufficient for many cases:

```python
def my_rule(verb, typ, ctx):
    if issubclass(typ, MyType):
        if verb == 'json_to_python':
            return typ.decoder
        elif verb == 'python_to_json':
            return typ.encoder
```

If your rule needs an encoder or decoder for a standard type, it can call
`ctx.lookup(verb=verb, typ=subtype)`. The helper functions defined in `json_syntax.action_v1`
are intended to stay the same so that custom rules can reuse them.

### Debugging amibguous structures

(May need more docs and some test cases.)

As _json-syntax_ tries to directly translate your Python types to JSON, it is possible
to write ambiguous structures. To avoid this, there is a handy `is_ambiguous` method:

```python
# This is true because both are represented as an array of numbers in JSON.
rules.is_ambiguous(typ=Union[List[int], Set[int]])

@dataclass
class Account:
    user: str
    address: str

# This is true because such a dictionary would always match the contents of the account.
rules.is_ambiguous(typ=Union[Dict[str, str], Account])
```

The aim of this is to let you put a check in your unit tests to make sure data can be
reliably expressed given your particular case.

Internally, this is using the `PATTERN` verb to represent the JSON pattern, so this may
be helpful in understanding how _json-syntax_ is trying to represent your data:

```python
print(rules.lookup(typ=MyAmbiguousClass, verb='show_pattern'))
```

### Sharp edges

_The RuleSet caches encoders._ Construct a new ruleset if you want to change settings.

_Encoders and decoders do very little checking._ Especially, if you're translating
Python to JSON, it's assumed that your Python classes are correct. The encoders and
decoders may mask subtle issues as they are calling constructors like `str` and `int`
for you. And, by design, if you're translating from JSON to Python, it's assumed you
want to be tolerant of extra data.

_Everything to do with typing._ It's a bit magical and sort of wasn't designed for this.
[We have a guide to it to try and help][types].

_Union types._ You can use `typing.Union` to allow a member to be one of some number of
alternates, but there are some caveats. You should use the `.is_ambiguous()` method of
RuleSet to warn you of these.

_Atom rules accept specific types._ At present, the rules for atomic types (`int`,
 `str`, `bool`, `date`, `float`, `Decimal`) must be declared as exactly those types. With
multiple inheritance, it's not clear which rule should apply

_Checks are stricter than converters._ For example, a check for `int` will check whether
the value is an integer, whereas the converter simply calls `int` on it. Thus there are
inputs for where `MyType` would pass but `Union[MyType, Dummy]` will fail. (Note
that `Optional` is special cased to look for `None` and doesn't have this problem.)

_Numbers are hard._ See the rules named `floats`, `floats_nan_str`, `decimals`,
`decimals_as_str` for details on how to get numbers to transmit reliably. There is no rule for
fractions or complex numbers as there's no canonical way to transmit them via JSON.

## Maintenance

This package is maintained via the [poetry][] tool. Some useful commands:

 1. Setup: `poetry install`
 2. Run tests: `poetry run pytest tests/`
 3. Reformat: `black json_syntax/ tests/`
 4. Generate setup.py: `dephell deps convert -e setup`
 5. Generate requirements.txt: `dephell deps convert -e req`

### Running tests via docker

The environments for 3.4 through 3.9 are in `pyproject.toml`, so just run:

    dephell deps convert -e req  # Create requirements.txt
    dephell docker run -e test34 pip install -r requirements.txt
    dephell docker run -e test34 pytest tests/
    dephell docker shell -e test34 pytest tests/
    dephell docker destroy -e test34

### Notes

<b id="f1">1</b>: Writing the encoder is deceptively easy because the instances in
Python have complete information. The standard `json` module provides a hook to let
you encode an object, and another hook to recognize `dict`s that have some special
attribute. This can work quite well, but you'll have to encode *all* non-JSON types
with dict-wrappers for the process to work in reverse. [↩](#a1)

<b id="f2">2</b>: A discriminated union has a tag that identifies the variant, such as
status codes that indicate success and a payload, or some error. Strictly, all unions
must be discriminated in some way if different code paths are executed. In the `unions`
rule, the discriminant is the class information in Python, and the structure of the JSON
data. A less flattering description would be that this is a "poorly" discriminated
union. [↩](#a2)

[poetry]: https://poetry.eustace.io/docs/#installation
[gradual typing]: https://www.python.org/dev/peps/pep-0483/#summary-of-gradual-typing
[the extras]: https://github.com/UnitedIncome/json-syntax/tree/master/json_syntax/extras
[typing]: https://docs.python.org/3/library/typing.html
[types]: https://github.com/UnitedIncome/json-syntax/blob/master/TYPES.md
[attrs]: https://attrs.readthedocs.io/en/stable/
[dataclasses]: https://docs.python.org/3/library/dataclasses.html
[sharp]: https://github.com/UnitedIncome/json-syntax/blob/master/README.md#sharp-edges
[ellipsis]: https://docs.python.org/3/library/stdtypes.html#the-ellipsis-object
[extras ddb]: https://github.com/UnitedIncome/json-syntax/tree/master/json_syntax/extras/dynamodb.py
[extras flag]: https://github.com/UnitedIncome/json-syntax/tree/master/json_syntax/extras/flags.py
[extras loose]: https://github.com/UnitedIncome/json-syntax/tree/master/json_syntax/extras/loose_dates.py
