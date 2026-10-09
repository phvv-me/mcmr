import polars as pl

from ...... import rule
from ......facts import FunctionFact, SyntaxFact
from ......query import CountQuery
from ......table import SyntaxRelation, Table
from ...gpu_relations import compiled_declarations, counted_syntax, record_constants


@rule("PY-NUMB0002")
def conditional_block_barrier(
    subject: Table[SyntaxFact],
    *,
    functions: Table[FunctionFact],
) -> CountQuery:
    """Count Numba block barriers reached through divergent control flow.

    Definition
    ----------
    Report `cuda.syncthreads()` inside a branch or loop in a function Numba compiles for the
    device, a kernel or a device function written with `cuda.jit` or with patos.cuda's `kernel`,
    `device`, and `ptx`, a record's methods included. A block barrier is valid only when every
    thread in the block reaches it, and a device function's barrier waits in every kernel that
    calls it. Thread-dependent control flow can leave part of the block waiting forever or produce
    undefined behavior.

    Evidence
    --------
    Each finding identifies the barrier and its function. The value is the number of block barriers
    nested in conditional or iterative control flow.

    Exceptions
    ----------
    Uniform conditions proven from block-invariant values may be safe, but the syntax alone cannot
    prove that uniformity. Keep such a barrier only with an explicit project waiver and evidence.
    A branch whose condition reads nothing but a patos.cuda record's `Constant[...]` fields,
    literals, and operators is the one uniformity the syntax does prove, since patos.cuda decides
    it when the kernel compiles, so a barrier under it is accepted.

    Examples
    --------
    Bad
    ~~~
    .. code-block:: python

       if cuda.threadIdx.x < active:
           cuda.syncthreads()

    Good
    ~~~~
    .. code-block:: python

       value = tile[cuda.threadIdx.x] if cuda.threadIdx.x < active else 0
       cuda.syncthreads()

    References
    ----------
    Cites "Numba CUDA documentation", CUDA Kernel API and synchronization
    https://nvidia.github.io/numba-cuda/reference/kernel.html#synchronization-and-atomic-operations
    Cites "CUDA C++ Programming Guide", synchronization functions
    https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#synchronization-functions
    """
    kernel_facts = compiled_declarations(subject, functions, "kernel", "device")
    nodes = subject.lazy(SyntaxRelation.NODES)
    barriers = nodes.filter(
        (pl.col("kind") == "call") & pl.col("name").str.ends_with(".syncthreads")
    ).select(
        "fact_id",
        pl.col("ordinal").alias("barrier_ordinal"),
        "path",
        "start_line",
        "start_column",
        "end_line",
        "end_column",
    )
    control = (
        nodes.filter(pl.col("kind").is_in(["branch", "loop"]))
        .select("fact_id", pl.col("ordinal").alias("control_ordinal"), "subtree_end")
        .join(
            _compiled_branches(subject, functions),
            on=["fact_id", "control_ordinal"],
            how="anti",
        )
    )
    selected = (
        barriers.join(control, on="fact_id", how="inner")
        .filter(
            (pl.col("control_ordinal") < pl.col("barrier_ordinal"))
            & (pl.col("barrier_ordinal") < pl.col("subtree_end"))
        )
        .unique(["fact_id", "barrier_ordinal"], maintain_order=True)
        .rename({"barrier_ordinal": "ordinal"})
        .join(kernel_facts, on="fact_id", how="inner")
    )
    return counted_syntax(
        subject,
        selected,
        pl.concat_str(
            pl.lit("Numba CUDA function `"),
            pl.col("qualname"),
            pl.lit("` reaches a block barrier conditionally"),
        ),
        "conditional block barrier",
    )


def _compiled_branches(subject: Table[SyntaxFact], functions: Table[FunctionFact]) -> pl.LazyFrame:
    """Return every branch whose condition reads only its record's `Constant[...]` fields."""
    nodes = subject.lazy(SyntaxRelation.NODES)
    conditions = (
        nodes.filter(pl.col("kind") == "branch")
        .select("fact_id", pl.col("ordinal").alias("control_ordinal"))
        .join(
            subject.lazy(SyntaxRelation.CHILDREN)
            .filter(pl.col("child_order") == 0)
            .select(
                "fact_id",
                pl.col("parent_ordinal").alias("control_ordinal"),
                pl.col("child_ordinal").alias("condition_ordinal"),
            ),
            on=["fact_id", "control_ordinal"],
            how="inner",
        )
        .join(
            nodes.select(
                "fact_id",
                pl.col("ordinal").alias("condition_ordinal"),
                pl.col("subtree_end").alias("condition_end"),
            ),
            on=["fact_id", "condition_ordinal"],
            how="inner",
        )
    )
    constants = record_constants(subject, functions).select(
        "fact_id", pl.col("field").alias("name"), pl.lit(True).alias("is_constant")
    )
    reads_constant = (pl.col("kind") == "member") & pl.col("is_constant")
    compiled = (
        pl.col("kind").is_in(["literal", "operation"])
        | ((pl.col("kind") == "name") & (pl.col("name") == "self"))
        | reads_constant
    )
    return (
        conditions.join(
            nodes.select("fact_id", "ordinal", "kind", "name"), on="fact_id", how="inner"
        )
        .filter(
            (pl.col("condition_ordinal") <= pl.col("ordinal"))
            & (pl.col("ordinal") < pl.col("condition_end"))
        )
        .join(constants, on=["fact_id", "name"], how="left")
        .with_columns(pl.col("is_constant").fill_null(False))
        .group_by("fact_id", "control_ordinal")
        .agg(compiled.all().alias("is_compiled"), reads_constant.any().alias("reads_constant"))
        .filter(pl.col("is_compiled") & pl.col("reads_constant"))
        .select("fact_id", "control_ordinal")
    )
