import pytest

from mcmr import validated_setting


def test_validation_cannot_introduce_an_unsupported_scalar() -> None:
    """Pydantic can convert text to bytes, but bytes cannot become a rule setting."""
    with pytest.raises(TypeError, match="Rule setting has unsupported type bytes"):
        validated_setting(bytes, "encoded")
