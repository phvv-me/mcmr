import ast
from collections import Counter


def import_bindings(tree: ast.Module) -> Counter[str]:
    """Count how often one parsed module binds each name through an import statement."""
    return Counter(
        (alias.asname or alias.name).split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    )
