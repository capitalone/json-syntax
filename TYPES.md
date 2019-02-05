# Type hints and generic types for the practitioner

One pitfall of type hints and generic types is they are different from what Python coders already know. Even if you were diligent and read the entire [tutorial][], they didn't get a mention and the standard library reference has them squirrled away under "development tools." They're obscure, but we need them<sup id="a1">[1](#f1)</sup> so we ought to explain them.

## What do they do?

Type hints are used by static type checkers like [mypy][] and [Pyre][] to prove that functions are passing the correct type of data to each other. They are the same concept as [TypeScript][] and [Flow][] in the Javascript world.

The premise of "gradual typing" is that it's optional. If code works, leave it alone. If you chase down a `TypeError`, though, you can add a few annotations directly in the source rather than write yet another unit test.

Generic types are the weird capitalized square bracketed types like `Dict[str, Tuple[int, ...]]` provided by the [typing][] module.

## What's the difference between a type, a type hint and a generic type?

In Python, the primary distinction is that type hints and generic types are not native to the interpreter.

To summarize them:

 * Types
    * The regular `int`, `bool`, `set`, `Decimal` you already know.
    * A **value** always has a type, so `5` is implicitly `int`.
    * Used extensively by the interpreter.
 * Type hints
    * Usually looks like `name: hint`.
    * Uses either a type or a generic type.
    * A **variable** _may_ have a hint.
    * Largely ignored by the interpreter.
    * (Also an argument to a function or member of a class has a hint.)
 * Generic types
    * Imported from [typing][].
    * Look like `FrozenSet[Decimal]`, `Dict[str, Tuple[int, str]]`.
    * Used in hints to describe the type of a variable with greater precision.

The reason for all this is that if you can nail down what kind of data is coming into a function, your code doesn't have to deal with all kinds of exceptional cases.

Python doesn't have a problem with a list like `[1, 2, 'three', 'four']`, but if you're trying to sum the elements of the list, it's going to fail because summation is only defined for numbers.

A generic type like `List[int]` is an assertion that the specific `list` will _only_ contain `int`s. A type checker can scan those assertions and look for contradictions. It's going to scan your code, finding those assertions and try to generate a proof that your code is sound _before_ you run it.

And just as type checkers can use type hints to generate proofs, json-syntax can unpack such assertions and write a converter based on the structure of the data.

## How do I use type hints in my code?

This document won't go into how type checkers use hints, and [mypy][] and [Pyre][] both have tutorials. In a nutshell, though, you can put hints in your function signatures.

For what we're trying to do, which is describe your data so you can convert it to and from JSON, the nicest way is through either the [attrs][] package or the (since 3.7) standard [dataclasses][] package. They're similar because `dataclasses` is a standardized `attrs`. It typically looks something like this:

```python
@attr.s(auto_attribs=True)
class Employee:
    name: str
    widgets_made: int

# Don't actually mix attrs and dataclasses,
# this is just to show they're similar.

@dataclass
class Department:
    name: str
    budget: float
    staff: List[Employee]

    @property
    def widgets_made(self):
        return sum(peon.widgets_made for peon in staff)
```

And what they do is write the `__dunder__` methods for you:

```python
>>> Employee('Bob', 55)  # __init__ and __repr__
Employee('Bob', 55)
>>> Employee('Bob', 55) == Employe('Bob', 55)  # comparisons
True
>>> {Employee('Bob', 55), Employee('Liz', 56)}  # __hash__
{Employee('Bob', 55), Employee('Liz', 56)}
```

That said, the type hints don't enforce anything by themselves:

```python
>>> Employee(name=123, widgets_made='wat?')
Employee(name=123, widgets_made='wat?')
```

But [mypy][mypy-add] and [Pyre][pyre-dc]<sup id="a4">[4](#f4)</sup> can use them to check the correctness of your code, and json-syntax uses them to write converters for you.

### Are generic types subclasses of their related types?

Let's ask Python:

```python
>>> issubclass(List[int], list)
TypeError: issubclass() arg 1 must be a class

>>> isinstance([1, 2, 3], List[int])
TypeError: Subscripted generics cannot be used with class and instance checks

>>> List[int]([1, 2, 3])
TypeError: Type List cannot be instantiated; use list() instead

>>> type(List[int])
<class 'typing._GenericAlias'>
```

Generic types are special objects that _describe_ types, but there's a twist. Let's check the method-resolution order of `List[int]` to list all the known base classes:

```python
>>> List[int].mro()
[<class 'list'>, <class 'object'>]
```

The `mro` method is only defined on `type`s, and it turns out `List[int]` *does* inherit from `list`. Weirder still:

```python
>>> class MyList(List[int]):
...     def average(self):
...         return sum(self) / len(self)

>>> MyList([1, 2, 3]).average()
2

>>> MyList.mro()
[<class '__main__.MyList'>, <class 'list'>, <class 'typing.Generic'>, <class 'object'>]
```

So it's valid for your own class to inherit from `List[int]`, whereupon it will behave like a `list`.

Your type checker can then enforce that your code only stores `int`s in that class for you.

At the time of writing, inheriting from a generic type won't work with json-syntax; we'll have to see if and how people want to use that.

## How does it work?

As an example, let's suppose we have a type hint `Set[date]` and we want to convert that back and forth between the Python representation and a reasonable<sup id="a2">[2](#f2)</sup> JSON representation.

```python
>>> json.loads('["2020-02-02", "2020-03-03", "2020-04-04"]')
['2020-02-02', '2020-03-03', '2020-04-04']
```

We want a decoder that will convert this to a Python set. And json-syntax will write us a function to do that based on the type hints:

```python
decoder = lookup(verb='json_to_python', typ=Set[date])

# Should result in equivalent to:

def decoder(value):
    return {date.fromisoformat(elem) for elem in data}

# And so we get our desired python values:

>>> decoder(['2020-02-02', '2020-03-03', '2020-04-04'])
{date(2020, 2, 2), date(2020, 3, 3), date(2020, 4, 4)}
```

### Under the hood

The algorithm can be visualized as transforming one tree into another.

```
    Type                 convert_type
   /    \    --->       /            \
 Type   Type       convert_type   convert_type


    Set            convert_set
     |     ---->       |
   date            convert_date
```

We can deconstruct complex types, like an `attrs` class:

```python
>>> [(a.name, a.type) for a in attrs.fields(Employee)]
[('name', str), ('widgets_made', int)]
```

Back to our example:

```python
decoder = lookup(verb='json_to_python', typ=Set[date])
```

We first need to take apart that generic `Set[date]`:

```python
>>> from typing import Set
>>> Set[date].__origin__
set
>>> Set[date].__args__
(date,)
```

We know it's a python `set` of something, and that it takes a single argument `date`.

The `sets` rule catches that we're dealing with a set, but it doesn't know how `date`s work, so it internally calls:

```python
inner = lookup(verb='json_to_python', typ=date)
```

The `dates` rule knows that `date` is an atom, it has no inner types to deal with. So it can simply return:

```python
def convert_date(value):
    return date.fromisoformat(value)
```

The `date.fromisoformat` method will parse a correctly formatted `str` to a `date`.

Now we're back in the `sets` rule and it knows that in the JSON representation it will have a `list` of something that it should convert to a `set`. Its action is a little less elegant than our original set comprehension:

```python
def convert_set(value, inner):
    return set(map(inner, value))
```

We use the [functools.partial][functools] builtin<sup id="a3">[3](#f3)</sup> to put this together, and wind up with an expression like:

```python
decoder = partial(convert_set, inner=convert_date)

# Same as:
def decoder(value):
    return convert_set(value, inner=convert_date)
```

### What are other generic types in `typing` for?

Some of the generic types are generic versions of abstract base classes from `collections` and others, which can be used to write custom classes, or to declare as little as possible. In the latter case, if your function just uses `for` to walk through the contents of an argument, it could hint that argument with `Iterable[Whatever]`.

This package doesn't have any standard rules supporting abstract types, as they seem like they'd suit specific use cases.

Type variables are used to allow types to change in lockstep. You might define a function `first` like this:

```python
T = TypeVar('T')
def first(elems: Iterable[T]) -> T:
    for elem in elems:
        return elem
```

The `T` may be different when the function is invoked in different contexts, but a type checker could infer from this that if `a: Set[str]` and `b = first(a)` that `b`'s type is `str`.

You can create a generic user-defined class with type variables. This package doesn't support type variables yet.

```python
@dataclass
class Pair(Generic[T]):
    a: T
    b: Set[T]

@dataclass
class Info:
    x: Pair[int]
    y: Pair[str]

# Effectively the same as:

@dataclass
class PairInt:
    a: int
    b: Set[int]

@dataclass
class PairStr:
    a: str
    b: Set[str]

@dataclass
class Info:
    x: PairInt
    y: PairStr
```

The `Union` generic type lets you select alternate types, and this is supported by json-syntax. There are some caveats, mentioned in the top level README.

## Footnotes

<b id="f1">1</b>: It's trivial to write an encoder that asks Python types to convert themselves to JSON, and `attrs`, `simplejson` and other libraries support this. Writing the decoder is trickier because you have to reconstruct that information. It can be done, it's how we did it before writing this library, but our experience was that it became a giant kludge over time.[↩](#a1)

<b id="f2">2</b>: This package defines "reasonable" as representing a set of dates as a JSON array of strings in the common ISO8601 format. You may have different needs, so you can swap in your own rules, and please submit a PR if you think they're addressing a broader need.[↩](#a2)

<b id="f3">3</b>: Using `partial` ensures that the converter can be pickled; not sure at this time if that's really helpful but it's easy to do. It should also make an `explain` function relatively easy to write.[↩](#a3)

<b id="f4">4</b>: Pyre only seems to support `dataclasses`.[↩](#a4)

[tutorial]: https://docs.python.org/3/tutorial/index.html
[dataclasses]: https://docs.python.org/3/library/dataclasses.html
[functools]: https://docs.python.org/3/library/functools.html
[typing]: https://docs.python.org/3/library/typing.html
[attrs]: https://attrs.readthedocs.io/en/stable/
[pyre]: https://pyre-check.org/
[pyre-dc]: https://github.com/facebook/pyre-check/blob/master/plugin/dataClass.ml
[mypy]: http://mypy-lang.org/
[mypy-add]: https://mypy.readthedocs.io/en/stable/additional_features.html
[typescript]: https://www.typescriptlang.org/
[flow]: https://flow.org/
