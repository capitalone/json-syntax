import attr
from enum import Enum
from typing import Mapping, Sequence


class FormEnum(Enum):
    '''
    A form is an overall representation. This class has no members to allow users to define their own forms.

    To make Trip.FOO_BAR work nicely, don't use underscores in member names.
    '''
    def __init_subclass__(cls):
        Form._register(cls)


class StdForm(FormEnum):
    '''
    Standard forms, python and json.
    '''
    PY = 'python'
    JS = 'json'


class FormRegistry:
    def __init__(self):
        self._uncached = []

    def __init_subclass__(cls):
        raise TypeError("Inherit from FormEnum; this class exists to enable an open enumeration.")

    def _register(self, cls):
        "This is generally called before the Enum class "
        if not issubclass(cls, FormEnum):
            raise TypeError("Can only register a subclass of FormEnum.")
        self._uncached.append(cls)

    def __getattr__(self, name):
        for cls in self._uncached:
            self.__dict__.update(cls.__members__)
        del self._uncached[:]
        return object.__getattribute__(self, name)

    def __setattr__(self, name):
        raise TypeError("Can't update the Form registry.")

    def __delattr__(self, name):
        raise TypeError("Can't update the Form registry.")


class _TripRegistry(type):
    def __getattr__(cls, name):
        result = None
        rname = None
        parts = name.split('_', 1)
        if len(parts) == 2 or '_' not in parts[1]:
            form_parts = [getattr(Form, part, None) for part in parts]
            if all(form_part is not None for form_part in form_parts):
                result = Trip(*form_parts)
                rname = '_'.join(reversed(parts))
        if result is None:
            raise AttributeError(f"type object {cls.__name__!r} has no attribute {name!r}")
        setattr(cls, name, result)
        setattr(cls, rname, result.reverse)
        return result


Form = FormRegistry()


@attr.s(frozen=True, auto_attrib=True)
class Trip(metaclass=_TripRegistry):
    '''
    A trip is one form to a different form.
    '''
    read: FormEnum
    write: FormEnum
    reverse: 'Trip' = attr.ib(repr=False)

    @reverse.default
    def _calc_reverse(self):
        return Trip(self.write, self.read, reverse=self)


@attr(frozen=True, auto_attrib=True)
class Behavior:
    '''
    Converters must:
     * know what pythonic type they deal with
     * know what form they accept and emit.
    '''
    trip: Trip  #: Identifies what form is converted to what
    subject: type  #: Identifies the python type being handled

    @property
    def read(self) -> Form:
        return trip.read

    @property
    def write(self) -> Form:
        return trip.write

    def reverse(self):
        return attr.evolve(self, trip=trip.reverse)

    def roundtrip(cls, trip, subject, name):
        behave = cls(trip=trip, subject=subject)
        return (behave, behave.reverse())


@attr(frozen=True, auto_attrib=True)
class OpenRegistry:
    registry: Mapping[Behavior, List[Converter]] = attr.ib(factory=lambda: defaultdict(list))

    def all_converters(self):
        for converters in registry.values():
            yield from converters

    def open_converters(self):
        return filter(lambda cvrt: not cvrt.specified, self.all_converters())
