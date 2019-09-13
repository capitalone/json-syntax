from typing import Any, Type
from .ruleset import SimpleRuleSet

def attrs_classes(
    verb: str,
    typ: Type[Any],
    ctx: SimpleRuleSet,
    pre_hook: str = "__json_pre_decode__",
    post_hook: str = "__json_post_encode__",
    check: str = "__json_check__",
) -> Any: ...
def named_tuples(verb: str, typ: Type[Any], ctx: SimpleRuleSet) -> Any: ...
def tuples(verb: str, typ: Type[Any], ctx: SimpleRuleSet) -> Any: ...
