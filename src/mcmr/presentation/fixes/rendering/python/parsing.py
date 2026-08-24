import ast

from .....domain.errors import UnrenderableFix


def parse_python(source: str, *, path: str) -> ast.Module:
    """Parse Python source and turn syntax failures into an autofix refusal."""
    try:
        return ast.parse(source, filename=path)
    except SyntaxError as error:
        raise UnrenderableFix(f"{path} does not parse as Python") from error
