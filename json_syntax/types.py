import attr
from enum import Enum
from typing import Mapping, Sequence


@attr.s(auto_attribs=True, frozen=True)
class Converter:
    '''
    An unspecified converter only knows what behavior it needs to fulfill, and can be replaced.
    '''
    behaviors: Tuple[Behavior, ...] = attr.ib(init=False, repr=False, converter=tuple)

    @behaviors.default
    def _calc_behaviors(self) -> Iterable[Behavior]:
        return tuple(self._behaviors())

    def _behaviors(self) -> Tuple[Behavior, ...]:
        raise NotImplementedError()

    specified = False

    def can_attempt(self, value, subject, trip):
        '''
        Checks optimistically if a value is convertable.

        By "optimistic" we mean that can_attempt may return True
        and convert still raises a ValueError.

        Caller responsibility:
          * Never call this for a subject or trip that is not listed under this type's behaviors.
        '''
        return True

    def convert(self, value, trip):
        '''
        Conversion may alternately:
         * convert a value and return the expected output
         * raise ValueError or a subclass to indicate a value it doesn't handle
         * raise other exceptions to indicate, e.g. logic problems
        '''
        return NotImplemented

    def params(self):
        '''
        Determine parameters for this converter. Atomic converters should not have open parameters.
        '''
        return ()

    def close_over(self, params):
        '''
        Return a new closed converter given the provided mapping of parameters.

        Contract:
          - Method may return self if no changes are made, but it may also return a copy.
          - Caller must ensure all params passed specify subclasses of Converter, not Convertable.
          - The new instance must replace any parameters listed with the Converters given.
        '''
        return self
