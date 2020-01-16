from .types import (  # noqa
    has_origin,
    get_origin,
    is_generic,
    issub_safe,
    NoneType,
    resolve_fwd_ref,
    python_minor,
)
from .errors import ErrorContext, err_ctx  # noqa

JSON2PY = "json_to_python"
PY2JSON = "python_to_json"
INSP_JSON = "inspect_json"
INSP_PY = "inspect_python"
INSP_STR = "inspect_string"
STR2PY = "string_to_python"
PY2STR = "python_to_string"
PATTERN = "show_pattern"
SENTINEL = object()


def identity(value):
    return value
