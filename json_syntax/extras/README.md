# The flags rule

This rule lets you use enums as strings without losing all Enums as the `faux_enums` rule does.

## Demonstrates

 * How to write a rule
 * How to write an action
 * How to write a fake type that's compatible with `typing.Union`

## Caveats

 * Requires Python 3.7
 * A user could mistakenly create a Flag instance
 * You'd probably be better off using enums
