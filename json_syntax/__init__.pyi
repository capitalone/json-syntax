from typing import Any, Callable, Tuple, Type, Union
from json_syntax.std import (
    atoms,
    decimals,
    decimals_as_str,
    floats,
    floats_nan_str,
    iso_dates,
    optional,
    enums,
    faux_enums,
    lists,
    sets,
    dicts,
)

def Rule(verb: str, typ: type, ctx: json_syntax.ruleset.SimpleRuleSet) -> Any: ...
def std_ruleset(
    floats=floats,
    decimals=decimals,
    dates=iso_dates,
    enums=enums,
    lists=lists,
    sets=sets,
    unions=unions,
    extras: Tuple[Rule] = (),
    custom: Type[RuleSet] = json_syntax.ruleset.RuleSet,
    cache=None,
): ...
