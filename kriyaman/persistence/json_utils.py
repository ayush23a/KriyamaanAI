from typing import Any
from pydantic_core import to_jsonable_python


def to_json_serializable(val: Any) -> Any:
    """Recursively convert any value (including Pydantic models, Decimal, UUID, datetime)
    into JSON-serializable Python primitives suitable for SQLAlchemy JSON columns."""
    if val is None:
        return None
    return to_jsonable_python(val)

