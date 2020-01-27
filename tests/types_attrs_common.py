from typing import TypeVar


class Hooks:
    @classmethod
    def __json_pre_decode__(cls, value):
        if isinstance(value, list):
            value = {"a": value[0], "b": value[1]}
        return value

    @classmethod
    def __json_check__(cls, value):
        return value.get("_type_") == "Hook"

    def __json_post_encode__(cls, value):
        return dict(value, _type_="Hook")


T = TypeVar("T")
U = TypeVar("U")
