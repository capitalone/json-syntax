import attr
from typing import Union, Optional, List

@attr.s(auto_attribs=True)
class CompositeThing:
    foo: Union[int, str]
    bar: List['Other']
    qux: Optional[int]


@attr.s(auto_attribs=True)
class Other:
    x: float
    y: float
    z: Optional[CompositeThing]


'''
So... we have a structure here.

What I want at the end of it is a classmethod or function that can encode an object as JSON, decode some JSON into the object.

And I might want to be able to swap in arbitrary functions for a given type.

Let's suppose we have a class called Generator that will scan a type and try to determine the correct rules.

I had been messing with the registry, but I was going in circles trying to figure out how to make the registry look up types through the `typing` API.

But I really don't need to. The Generator class can be a list of matchers. One would handle collection types, another would look at attrs, another basic types. And you'd insert overrides where you wanted them, or subclass it to inject your logic. (Could be that types specify their own Generator, too, since a discovery mechanism could just look for `.discovery` on the type.)

And one of those methods could look in a registry for specific type instances to see if an encode / decode mechanism already existed for them, and it could keep this up to date as it's building encoders and decoders.

The call we're going to make is `Generator.generate_encoder(root_type)`. We first call:

>>> reg = SimpleRegistry()
>>> gen = Generator()
>>> gen.use(reg)
>>> gen.use(basic_types)
>>> gen.use(attrs_types)
>>> gen.use(collection_types)
>>> gen.notify(add_classmethods)
>>> gen.notify(reg)
