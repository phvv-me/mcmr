import polars as pl

from ...... import rule
from ......facts import FunctionFact, SyntaxFact
from ......query import CountQuery
from ......table import SyntaxRelation, Table
from ...gpu_relations import compiled_declarations, counted_syntax


@rule("PY-NUMB0001")
def kernel_return_value(
    subject: Table[SyntaxFact],
    *,
    functions: Table[FunctionFact],
) -> CountQuery:
    """Count explicit values returned from Numba CUDA kernels.

    Definition
    ----------
    Report a `return` statement with a value inside a function compiled as a kernel, by Numba's
    `cuda.jit` or by patos.cuda's `kernel`, a record's kernel methods included. CUDA kernels cannot
    return values to their host caller. Results must be written through an array or device buffer
    passed to the kernel.

    Evidence
    --------
    Each finding identifies the returning statement and its kernel. The value is the number of
    explicit return values in the kernel.

    Exceptions
    ----------
    A bare `return` is accepted because it only stops the current thread. A device function,
    compiled with `device=True` or patos.cuda's `device`, is also accepted because device functions
    may return values.

    Examples
    --------
    Bad
    ~~~
    .. code-block:: python

       @cuda.jit
       def total(values):
           return values[cuda.grid(1)]

    Good
    ~~~~
    .. code-block:: python

       @cuda.jit
       def total(values, output):
           output[cuda.grid(1)] = values[cuda.grid(1)]

    References
    ----------
    Cites "Numba CUDA documentation", writing CUDA kernels and kernel declaration
    https://nvidia.github.io/numba-cuda/user/kernels.html#kernel-declaration
    """
    kernel_facts = compiled_declarations(subject, functions, "kernel")
    returned_values = (
        subject.lazy(SyntaxRelation.NODES)
        .filter(pl.col("kind") == "return")
        .join(
            subject.lazy(SyntaxRelation.CHILDREN).select(
                "fact_id", pl.col("parent_ordinal").alias("ordinal")
            ),
            on=["fact_id", "ordinal"],
            how="inner",
        )
        .unique(["fact_id", "ordinal"], maintain_order=True)
        .join(kernel_facts, on="fact_id", how="inner")
    )
    return counted_syntax(
        subject,
        returned_values,
        pl.concat_str(
            pl.lit("Numba CUDA kernel `"),
            pl.col("qualname"),
            pl.lit("` returns a value"),
        ),
        "kernel return value",
    )
