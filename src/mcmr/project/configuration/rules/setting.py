from typing import TYPE_CHECKING

from pydantic import TypeAdapter

if TYPE_CHECKING:
    from typing_extensions import TypeForm

    from ....domain.contracts import RuleSetting


def validated_setting[T](annotation: TypeForm[T], value: RuleSetting) -> RuleSetting:
    """Validate one setting against its rule annotation and retain supported value shapes."""
    answer = TypeAdapter[T](annotation).validate_python(value)
    if isinstance(answer, bool | int | float | str):
        return answer
    if isinstance(answer, tuple | list | set):
        strings = [item for item in answer if isinstance(item, str)]
        if len(strings) == len(answer):
            return set(strings) if isinstance(answer, set) else strings
    raise TypeError(f"Rule setting has unsupported type {type(answer).__name__}")
