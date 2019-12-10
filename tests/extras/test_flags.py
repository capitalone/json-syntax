import pytest
from tests.common import Rules

from json_syntax.extras import flags as fl
from json_syntax.helpers import (
    JSON2PY,
    PY2JSON,
    INSP_JSON,
    INSP_PY,
    STR2PY,
    PY2STR,
    INSP_STR,
    python_minor,
)


@pytest.mark.skipif(
    python_minor < (3, 7), reason="__class_getitem__ not supported before 3.7"
)
@pytest.mark.parametrize("verb", [JSON2PY, PY2JSON, STR2PY, PY2STR])
def test_Flag_getitem_convert(verb):
    action = fl.flags(verb=verb, typ=fl.Flag["foo", "bar", "qux"], ctx=Rules())
    assert action("foo") == "foo"
    assert action("qux") == "qux"

    with pytest.raises(ValueError):
        action("nope")


@pytest.mark.parametrize("verb", [JSON2PY, PY2JSON, STR2PY, PY2STR])
def test_Flag_init_convert(verb):
    action = fl.flags(verb=verb, typ=fl.Flag("foo", "bar", "qux"), ctx=Rules())
    assert action("foo") == "foo"
    assert action("qux") == "qux"

    with pytest.raises(ValueError):
        action("nope")


@pytest.mark.skipif(
    python_minor < (3, 7), reason="__class_getitem__ not supported before 3.7"
)
@pytest.mark.parametrize("verb", [INSP_PY, INSP_JSON, INSP_STR])
def test_Flag_getitem_inspect(verb):
    action = fl.flags(verb=verb, typ=fl.Flag["foo", "bar", "qux"], ctx=Rules())
    assert action("foo")
    assert action("qux")
    assert not action("nope")


@pytest.mark.parametrize("verb", [INSP_PY, INSP_JSON, INSP_STR])
def test_Flag_init_inspect(verb):
    action = fl.flags(verb=verb, typ=fl.Flag("foo", "bar", "qux"), ctx=Rules())
    assert action("foo")
    assert action("qux")
    assert not action("nope")
